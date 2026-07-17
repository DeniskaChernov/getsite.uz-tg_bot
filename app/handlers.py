"""Пользовательские хендлеры: /start с payload, диалог через LLM, edge cases."""
from __future__ import annotations

import asyncio
import logging
import re

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import texts
from app.config import config
from app.leads import send_lead
from app.llm import (
    MAX_INPUT_CHARS,
    LLMBusy,
    LLMFiltered,
    brief_is_complete,
    extract_brief,
    generate_reply,
)
from app.ratelimit import limiter
from app.services import resolve_payload
from app.storage import Storage

log = logging.getLogger(__name__)
router = Router()

_FORGET_RE = re.compile(
    r"(удали(те)?\s+мои\s+данные|delete\s+my\s+data|ma'?lumotlarimni\s+o'?chir)", re.IGNORECASE
)


def _quick_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=cb)] for t, cb in texts.QUICK_BUTTONS[lang]
    ])


async def _user_lang(storage: Storage, message: Message) -> str:
    user = await storage.get_user(message.from_user.id)
    if user:
        return user["lang"]
    return texts.normalize_lang(message.from_user.language_code)


# --- группы/каналы: бот работает только в личке ---

@router.my_chat_member(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL}))
async def on_added_to_group(event, bot: Bot):
    if event.chat.id == config.admin_chat_id:
        return
    log.info("Added to foreign chat %s, leaving", event.chat.id)
    try:
        await bot.leave_chat(event.chat.id)
    except Exception:
        log.warning("Failed to leave chat %s", event.chat.id, exc_info=True)


@router.message(F.chat.type != ChatType.PRIVATE)
async def ignore_non_private(message: Message):
    return


# --- /start ---

@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start(message: Message, command: CommandObject, storage: Storage):
    if message.from_user.is_bot:
        return
    lang = texts.normalize_lang(message.from_user.language_code)
    existing = await storage.get_user(message.from_user.id)
    if existing:
        lang = existing["lang"]

    svc = resolve_payload(command.args)
    await storage.upsert_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name,
        lang, payload=svc.payload,
    )
    await storage.log_event("start", message.from_user.id, svc.payload)

    # Мгновенный шаблон без LLM
    if svc.payload == "discuss":
        text = texts.START_NO_PAYLOAD[lang]
    else:
        text = texts.start_with_service(svc, lang)
    await storage.add_message(message.from_user.id, "assistant", text)
    await message.answer(text, reply_markup=_quick_kb(lang))


# --- сервисные команды ---

@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def cmd_help(message: Message, storage: Storage):
    lang = await _user_lang(storage, message)
    await message.answer(texts.HELP_REPLY[lang])


@router.message(Command("lang"), F.chat.type == ChatType.PRIVATE)
async def cmd_lang(message: Message, command: CommandObject, storage: Storage):
    lang = (command.args or "").strip().lower()
    if lang not in ("ru", "uz", "en"):
        current = await _user_lang(storage, message)
        await message.answer(texts.HELP_REPLY[current])
        return
    await storage.upsert_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name, lang,
    )
    await storage.set_lang(message.from_user.id, lang)
    await message.answer(texts.LANG_CHANGED[lang])


# --- inline-кнопки быстрого ответа ---

@router.callback_query(F.data == "qb_contact")
async def cb_contact(query: CallbackQuery, storage: Storage):
    user = await storage.get_user(query.from_user.id)
    lang = user["lang"] if user else texts.normalize_lang(query.from_user.language_code)
    await query.answer()
    await query.message.answer(texts.CONTACT_REPLY[lang])
    await storage.add_message(query.from_user.id, "assistant", texts.CONTACT_REPLY[lang])


@router.callback_query(F.data.in_({"qb_estimate", "qb_timeline"}))
async def cb_quick(query: CallbackQuery, bot: Bot, storage: Storage):
    user = await storage.get_user(query.from_user.id)
    lang = user["lang"] if user else texts.normalize_lang(query.from_user.language_code)
    await query.answer()
    user_text = texts.QUICK_BUTTON_AS_USER_TEXT[query.data][lang]
    await _dialog_turn(bot, storage, query.from_user.id, query.message.chat.id, user_text, lang)


# --- медиа и прочий не-текст ---

@router.message(F.chat.type == ChatType.PRIVATE,
                F.photo | F.voice | F.video | F.document | F.audio | F.video_note)
async def on_media(message: Message, storage: Storage):
    if message.from_user.is_bot or message.forward_origin:
        return
    lang = await _user_lang(storage, message)
    await message.answer(texts.MEDIA_REPLY[lang])


@router.message(F.chat.type == ChatType.PRIVATE, F.sticker)
async def on_sticker(message: Message):
    return


# --- основной диалог ---

@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def on_text(message: Message, bot: Bot, storage: Storage):
    # Анти-спам: пересланное и сообщения от ботов игнорируем
    if message.from_user.is_bot or message.forward_origin:
        return
    user = await storage.get_user(message.from_user.id)
    if user and user.get("muted"):
        return
    lang = user["lang"] if user else texts.normalize_lang(message.from_user.language_code)
    if not user:
        await storage.upsert_user(
            message.from_user.id, message.from_user.username, message.from_user.first_name, lang,
        )

    text = message.text

    # «Удалите мои данные» → подтверждение + задача админу
    if _FORGET_RE.search(text):
        await message.answer(texts.FORGET_CONFIRM_USER[lang])
        try:
            await bot.send_message(
                config.admin_chat_id,
                f"🗑 Запрос на удаление данных от id {message.from_user.id} "
                f"(@{message.from_user.username or '—'}). Выполните: /forget {message.from_user.id}",
            )
        except Exception:
            log.error("Failed to notify admins about forget request", exc_info=True)
        return

    # Rate-limit без LLM
    if not limiter.check_user(message.from_user.id):
        await message.answer(texts.RATE_LIMIT_REPLY[lang])
        return

    if len(text) > MAX_INPUT_CHARS:
        await message.answer(texts.TOO_LONG_REPLY[lang])
        text = text[:MAX_INPUT_CHARS]

    await _dialog_turn(bot, storage, message.from_user.id, message.chat.id, text, lang)


async def _dialog_turn(bot: Bot, storage: Storage, user_id: int, chat_id: int,
                       user_text: str, lang: str) -> None:
    """Один ход диалога: LLM-ответ + детерминированная проверка готовности брифа."""
    await storage.add_message(user_id, "user", user_text)

    # Circuit breaker: всплеск трафика → шаблон без LLM + алерт
    if not limiter.check_global():
        await bot.send_message(chat_id, texts.LLM_FALLBACK_REPLY[lang])
        if not getattr(limiter, "_alerted", False):
            limiter._alerted = True
            try:
                await bot.send_message(config.admin_chat_id,
                                       "⚠️ Circuit breaker открыт: аномальный всплеск трафика, LLM отключён на 5 минут.")
            except Exception:
                pass
        return
    limiter._alerted = False

    user = await storage.get_user(user_id)
    svc = resolve_payload(user.get("payload") if user else None)
    brief = await storage.get_brief(user_id)
    brief_state = ", ".join(f"{k}: {v}" for k, v in brief.items()
                            if v and not k.startswith("_")) or "пусто"
    history = await storage.history(user_id)

    try:
        await bot.send_chat_action(chat_id, "typing")
        reply = await generate_reply(
            user_id, history,
            svc.name_ru if svc.payload != "discuss" else None,
            lang, brief_state,
        )
    except LLMBusy:
        await bot.send_message(chat_id, texts.RATE_LIMIT_REPLY[lang])
        return
    except LLMFiltered as e:
        await storage.log_event("filter_hit", user_id, e.reason)
        await bot.send_message(chat_id, texts.FILTERED_REPLY[lang])
        return
    except (asyncio.TimeoutError, Exception):
        log.error("LLM failed for user %s", user_id, exc_info=True)
        await storage.log_event("llm_error", user_id)
        await bot.send_message(chat_id, texts.LLM_FALLBACK_REPLY[lang])
        return

    await storage.add_message(user_id, "assistant", reply)
    await bot.send_message(chat_id, reply)

    # Детерминированная передача лида: извлекаем бриф кодом, не моделью
    if brief.get("_lead_sent"):
        return
    extracted = await extract_brief(await storage.history(user_id))
    if extracted:
        merged = {**brief, **{k: v for k, v in extracted.items() if v}}
        await storage.save_brief(user_id, merged)
        if brief_is_complete(merged):
            merged["_lead_sent"] = True
            await storage.save_brief(user_id, merged)
            await storage.log_event("brief_done", user_id)
            await send_lead(bot, storage, user_id)
            await bot.send_message(chat_id, texts.LEAD_CONFIRM_USER[lang])
