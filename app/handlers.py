"""Пользовательские хендлеры: регистрация (язык → имя → телефон), диалог, edge cases."""
from __future__ import annotations

import asyncio
import logging
import re

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app import texts
from app.brief_flow import format_brief_summary, is_confirmation, is_edit_request
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
from app.storage import REG_DONE, REG_NEED_LANG, REG_NEED_NAME, REG_NEED_PHONE, BotStorage

log = logging.getLogger(__name__)
router = Router()

_FORGET_RE = re.compile(
    r"(удали(те)?\s+мои\s+данные|delete\s+my\s+data|ma'?lumotlarimni\s+o'?chir)", re.IGNORECASE
)
_PHONE_DIGITS_RE = re.compile(r"\d")


def _quick_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=cb)] for t, cb in texts.QUICK_BUTTONS[lang]
    ])


def _lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=cb)] for t, cb in texts.LANG_BUTTONS
    ])


def _confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.CONFIRM_YES_BTN[lang], callback_data="brief_yes")],
        [InlineKeyboardButton(text=texts.CONFIRM_EDIT_BTN[lang], callback_data="brief_edit")],
    ])


def _phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.SHARE_PHONE_BTN[lang], request_contact=True)],
            [KeyboardButton(text=texts.SKIP_BTN[lang])],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _service_greeting(bot: Bot, storage: BotStorage, user_id: int, chat_id: int,
                            lang: str, prefix: str = "") -> None:
    """Приветствие по услуге из payload (шаблон, без LLM) + быстрые кнопки."""
    user = await storage.get_user(user_id)
    svc = resolve_payload(user.get("payload") if user else None)
    if svc.payload == "discuss":
        text = texts.START_NO_PAYLOAD[lang]
    else:
        text = texts.start_with_service(svc, lang)
    if prefix:
        text = f"{prefix} {text}"
    await storage.add_message(user_id, "assistant", text)
    await bot.send_message(chat_id, text, reply_markup=_quick_kb(lang))


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


# --- /start: сначала выбор языка, потом регистрация ---

@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start(message: Message, bot: Bot, command: CommandObject, storage: BotStorage):
    if message.from_user.is_bot:
        return
    svc = resolve_payload(command.args)
    existing = await storage.get_user(message.from_user.id)
    lang = existing["lang"] if existing else texts.normalize_lang(message.from_user.language_code)

    await storage.upsert_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name,
        lang, payload=svc.payload,
    )
    await storage.log_event("start", message.from_user.id, svc.payload)

    # Зарегистрированный клиент: помним его, здороваемся по имени и сразу к делу.
    # Сбрасываем флаги прошлого лида - можно начать новую заявку.
    if existing and existing.get("reg_state") == REG_DONE:
        await storage.reset_lead_flags(message.from_user.id)
        prefix = texts.WELCOME_BACK[lang].format(name=existing.get("name") or existing.get("first_name") or "")
        await _service_greeting(bot, storage, message.from_user.id, message.chat.id, lang, prefix)
        return

    # Новый клиент: выбор языка первым сообщением
    await storage.set_reg_state(message.from_user.id, REG_NEED_LANG)
    await message.answer(texts.CHOOSE_LANG, reply_markup=_lang_kb())


@router.callback_query(F.data.startswith("lang_"))
async def cb_lang(query: CallbackQuery, bot: Bot, storage: BotStorage):
    lang = query.data.removeprefix("lang_")
    if lang not in ("ru", "uz", "en"):
        await query.answer()
        return
    user = await storage.get_user(query.from_user.id)
    if not user:
        await storage.upsert_user(query.from_user.id, query.from_user.username,
                                  query.from_user.first_name, lang)
        user = await storage.get_user(query.from_user.id)
    await storage.set_lang(query.from_user.id, lang)
    await query.answer()
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Смена языка после регистрации - просто подтверждение
    if user.get("reg_state") == REG_DONE:
        await bot.send_message(query.message.chat.id, texts.LANG_CHANGED[lang])
        return

    await storage.set_reg_state(query.from_user.id, REG_NEED_NAME)
    await bot.send_message(query.message.chat.id, texts.ASK_NAME[lang])


# --- сервисные команды ---

@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def cmd_help(message: Message, storage: BotStorage):
    user = await storage.get_user(message.from_user.id)
    lang = user["lang"] if user else texts.normalize_lang(message.from_user.language_code)
    await message.answer(texts.HELP_REPLY[lang])


@router.message(Command("lang"), F.chat.type == ChatType.PRIVATE)
async def cmd_lang(message: Message, command: CommandObject, storage: BotStorage):
    lang = (command.args or "").strip().lower()
    if lang not in ("ru", "uz", "en"):
        await message.answer(texts.CHOOSE_LANG, reply_markup=_lang_kb())
        return
    await storage.upsert_user(message.from_user.id, message.from_user.username,
                              message.from_user.first_name, lang)
    await storage.set_lang(message.from_user.id, lang)
    await message.answer(texts.LANG_CHANGED[lang])


# --- inline-кнопки быстрого ответа ---

@router.callback_query(F.data == "qb_contact")
async def cb_contact(query: CallbackQuery, storage: BotStorage):
    user = await storage.get_user(query.from_user.id)
    if user and user.get("muted"):
        await query.answer()
        return
    lang = user["lang"] if user else texts.normalize_lang(query.from_user.language_code)
    await query.answer()
    await query.message.answer(texts.CONTACT_REPLY[lang])
    await storage.add_message(query.from_user.id, "assistant", texts.CONTACT_REPLY[lang])


@router.callback_query(F.data.in_({"qb_estimate", "qb_timeline"}))
async def cb_quick(query: CallbackQuery, bot: Bot, storage: BotStorage):
    user = await storage.get_user(query.from_user.id)
    if user and user.get("muted"):
        await query.answer()
        return
    lang = user["lang"] if user else texts.normalize_lang(query.from_user.language_code)
    await query.answer()
    user_text = texts.QUICK_BUTTON_AS_USER_TEXT[query.data][lang]
    await _dialog_turn(bot, storage, query.from_user.id, query.message.chat.id, user_text, lang)


@router.callback_query(F.data == "brief_yes")
async def cb_brief_yes(query: CallbackQuery, bot: Bot, storage: BotStorage):
    user = await storage.get_user(query.from_user.id)
    if user and user.get("muted"):
        await query.answer()
        return
    lang = user["lang"] if user else texts.normalize_lang(query.from_user.language_code)
    brief = await storage.get_brief(query.from_user.id)
    # Старая кнопка после «Нужно поправить» или уже отправленный лид - игнор
    if brief.get("_lead_sent") or not brief.get("_awaiting_confirm"):
        await query.answer("Сначала сверим актуальные данные" if lang == "ru" else "OK")
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return
    await query.answer()
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _finalize_confirmed_lead(bot, storage, query.from_user.id, query.message.chat.id, lang)


@router.callback_query(F.data == "brief_edit")
async def cb_brief_edit(query: CallbackQuery, storage: BotStorage):
    user = await storage.get_user(query.from_user.id)
    if user and user.get("muted"):
        await query.answer()
        return
    lang = user["lang"] if user else texts.normalize_lang(query.from_user.language_code)
    await query.answer()
    brief = await storage.get_brief(query.from_user.id)
    brief.pop("_awaiting_confirm", None)
    await storage.save_brief(query.from_user.id, brief)
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.answer(texts.BRIEF_EDIT_REPLY[lang])
    await storage.add_message(query.from_user.id, "assistant", texts.BRIEF_EDIT_REPLY[lang])


# --- контакт (шаг регистрации: телефон) ---

@router.message(F.chat.type == ChatType.PRIVATE, F.contact)
async def on_contact(message: Message, bot: Bot, storage: BotStorage):
    user = await storage.get_user(message.from_user.id)
    if not user:
        return
    lang = user["lang"]
    if user.get("reg_state") == REG_NEED_PHONE and message.contact.user_id == message.from_user.id:
        await storage.set_phone(message.from_user.id, message.contact.phone_number)
        await _finish_registration(bot, storage, message, lang)


async def _finish_registration(bot: Bot, storage: BotStorage, message: Message, lang: str) -> None:
    await storage.set_reg_state(message.from_user.id, REG_DONE)
    await storage.log_event("registered", message.from_user.id)
    await message.answer(texts.REG_DONE_PREFIX[lang], reply_markup=ReplyKeyboardRemove())
    await _service_greeting(bot, storage, message.from_user.id, message.chat.id, lang)


# --- медиа и прочий не-текст ---

@router.message(F.chat.type == ChatType.PRIVATE,
                F.photo | F.voice | F.video | F.document | F.audio | F.video_note)
async def on_media(message: Message, storage: BotStorage):
    if message.from_user.is_bot or message.forward_origin:
        return
    user = await storage.get_user(message.from_user.id)
    lang = user["lang"] if user else texts.normalize_lang(message.from_user.language_code)
    await message.answer(texts.MEDIA_REPLY[lang])


@router.message(F.chat.type == ChatType.PRIVATE, F.sticker)
async def on_sticker(message: Message):
    return


# --- основной текстовый поток ---

@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def on_text(message: Message, bot: Bot, storage: BotStorage):
    if message.from_user.is_bot or message.forward_origin:
        return
    user = await storage.get_user(message.from_user.id)
    if user and user.get("muted"):
        return
    lang = user["lang"] if user else texts.normalize_lang(message.from_user.language_code)
    if not user:
        await storage.upsert_user(message.from_user.id, message.from_user.username,
                                  message.from_user.first_name, lang)
        user = await storage.get_user(message.from_user.id)

    text = message.text.strip()
    reg_state = user.get("reg_state") or REG_NEED_LANG

    # --- шаги регистрации ---
    if reg_state == REG_NEED_LANG:
        await message.answer(texts.CHOOSE_LANG, reply_markup=_lang_kb())
        return

    if reg_state == REG_NEED_NAME:
        if len(text) > 50 or text.startswith("/"):
            await message.answer(texts.NAME_TOO_LONG[lang])
            return
        await storage.set_name(message.from_user.id, text)
        await message.answer(texts.ASK_PHONE[lang].format(name=text), reply_markup=_phone_kb(lang))
        await storage.set_reg_state(message.from_user.id, REG_NEED_PHONE)
        return

    if reg_state == REG_NEED_PHONE:
        digits = "".join(_PHONE_DIGITS_RE.findall(text))
        if text != texts.SKIP_BTN[lang] and 9 <= len(digits) <= 15:
            await storage.set_phone(message.from_user.id, "+" + digits if not text.startswith("+") else text)
        await _finish_registration(bot, storage, message, lang)
        return

    # --- обычный диалог ---

    if _FORGET_RE.search(text):
        await message.answer(texts.FORGET_CONFIRM_USER[lang])
        try:
            await bot.send_message(
                config.admin_chat_id,
                f"🗑 Запрос на удаление данных от id {message.from_user.id} "
                f"(@{message.from_user.username or '-'}). Выполните: /forget {message.from_user.id}",
            )
        except Exception:
            log.error("Failed to notify admins about forget request", exc_info=True)
        return

    if not limiter.check_user(message.from_user.id):
        await message.answer(texts.RATE_LIMIT_REPLY[lang])
        return

    if len(text) > MAX_INPUT_CHARS:
        await message.answer(texts.TOO_LONG_REPLY[lang])
        text = text[:MAX_INPUT_CHARS]

    await _dialog_turn(bot, storage, message.from_user.id, message.chat.id, text, lang)


async def _dialog_turn(bot: Bot, storage: BotStorage, user_id: int, chat_id: int,
                       user_text: str, lang: str) -> None:
    """Один ход диалога: LLM-ответ + сводка брифа → подтверждение → лид."""
    brief = await storage.get_brief(user_id)

    # Уже ждём подтверждения сводки: да → лид, нет/правка → продолжаем сбор
    if brief.get("_awaiting_confirm") and not brief.get("_lead_sent"):
        if is_confirmation(user_text):
            await storage.add_message(user_id, "user", user_text)
            await _finalize_confirmed_lead(bot, storage, user_id, chat_id, lang)
            return
        if is_edit_request(user_text):
            await storage.add_message(user_id, "user", user_text)
            brief.pop("_awaiting_confirm", None)
            await storage.save_brief(user_id, brief)
            await bot.send_message(chat_id, texts.BRIEF_EDIT_REPLY[lang])
            await storage.add_message(user_id, "assistant", texts.BRIEF_EDIT_REPLY[lang])
            return
        # Клиент пишет что-то ещё - снимаем ожидание и продолжаем диалог
        brief.pop("_awaiting_confirm", None)
        await storage.save_brief(user_id, brief)

    await storage.add_message(user_id, "user", user_text)

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
            client_name=(user.get("name") if user else None),
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

    # Когда бриф собран - показываем сводку и ждём явного подтверждения.
    # Лид уходит только после "Да, подтверждаю".
    if brief.get("_lead_sent") or brief.get("_awaiting_confirm"):
        return
    fresh_history = await storage.history(user_id, limit=50)
    user_msg_count = sum(1 for m in fresh_history if m["role"] == "user")
    extracted = await extract_brief(fresh_history)
    if extracted:
        merged = {**brief, **{k: v for k, v in extracted.items() if v}}
        await storage.save_brief(user_id, merged)
        if brief_is_complete(merged, user_msg_count):
            merged["_awaiting_confirm"] = True
            await storage.save_brief(user_id, merged)
            summary = format_brief_summary(merged, lang)
            await bot.send_message(chat_id, summary, reply_markup=_confirm_kb(lang))
            await storage.add_message(user_id, "assistant", summary)
            await storage.log_event("brief_ready", user_id)


async def _finalize_confirmed_lead(bot: Bot, storage: BotStorage, user_id: int,
                                   chat_id: int, lang: str) -> None:
    brief = await storage.get_brief(user_id)
    if brief.get("_lead_sent"):
        await bot.send_message(chat_id, texts.LEAD_CONFIRM_USER[lang])
        return
    # Атомарный claim: только один параллельный апдейт сможет поставить флаг
    if not await storage.claim_lead(user_id):
        await bot.send_message(chat_id, texts.LEAD_CONFIRM_USER[lang])
        return
    await storage.log_event("brief_done", user_id)
    lead_id = await send_lead(bot, storage, user_id)
    if lead_id is None:
        # Откат, чтобы можно было повторить подтверждение
        brief = await storage.get_brief(user_id)
        brief.pop("_lead_sent", None)
        brief["_awaiting_confirm"] = True
        await storage.save_brief(user_id, brief)
        await bot.send_message(chat_id, texts.LLM_FALLBACK_REPLY[lang])
        return
    await bot.send_message(chat_id, texts.LEAD_CONFIRM_USER[lang])
    await storage.add_message(user_id, "assistant", texts.LEAD_CONFIRM_USER[lang])
