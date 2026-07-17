"""Админ-команды и кнопки карточек лидов. Доступ - только по user_id из allowlist."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app.config import config
from app.storage import BotStorage

log = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("leads"))
async def cmd_leads(message: Message, storage: BotStorage):
    if not _is_admin(message.from_user.id):
        return
    leads = await storage.recent_leads(10)
    if not leads:
        await message.answer("Лидов пока нет.")
        return
    lines = []
    for lead in leads:
        ts = datetime.fromtimestamp(lead["created_at"], tz=timezone.utc).strftime("%d.%m %H:%M")
        lines.append(f"#{lead['id']} [{lead['status']}] {ts} - id {lead['user_id']}, "
                     f"payload {lead['payload'] or '-'}: {lead['summary'][:100]}")
    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message, storage: BotStorage):
    if not _is_admin(message.from_user.id):
        return
    s = await storage.stats(7)
    events = s["events"]
    starts = sum(s["starts_by_payload"].values())
    by_payload = "\n".join(f"  {p}: {c}" for p, c in
                           sorted(s["starts_by_payload"].items(), key=lambda x: -x[1])) or "  -"
    await message.answer(
        f"📊 За 7 дней:\n"
        f"Стартов: {starts}\n{by_payload}\n"
        f"Регистраций: {events.get('registered', 0)}\n"
        f"Брифов собрано: {events.get('brief_done', 0)}\n"
        f"Лидов передано: {s['leads']}\n"
        f"Ошибок LLM: {events.get('llm_error', 0)}\n"
        f"Срабатываний фильтра: {events.get('filter_hit', 0)}"
    )


@router.message(Command("forget"))
async def cmd_forget(message: Message, command: CommandObject, storage: BotStorage):
    if not _is_admin(message.from_user.id):
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Использование: /forget <user_id>")
        return
    user_id = int(command.args.strip())
    await storage.forget_user(user_id)
    log.info("Admin %s forgot user %s", message.from_user.id, user_id)
    await message.answer(f"Данные пользователя {user_id} удалены.")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject, storage: BotStorage):
    if not _is_admin(message.from_user.id):
        return
    args = (command.args or "").split()
    if not args or not args[0].isdigit():
        await message.answer("Использование: /mute <user_id> [off]")
        return
    user_id = int(args[0])
    unmute = len(args) > 1 and args[1] == "off"
    await storage.set_muted(user_id, not unmute)
    await message.answer(f"Пользователь {user_id} {'размьючен' if unmute else 'замьючен'}.")


# --- кнопки под карточкой лида ---

@router.callback_query(F.data.startswith("lead_take:"))
async def cb_lead_take(query: CallbackQuery, storage: BotStorage):
    if not _is_admin(query.from_user.id):
        await query.answer("Нет доступа", show_alert=True)
        return
    lead_id = int(query.data.split(":")[1])
    await storage.set_lead_status(lead_id, "taken", query.from_user.id)
    who = query.from_user.first_name or query.from_user.username or query.from_user.id
    await query.answer("Взято в работу")
    await query.message.edit_text(f"{query.message.text}\n\n✅ Взял в работу: {who}")


@router.callback_query(F.data.startswith("lead_spam:"))
async def cb_lead_spam(query: CallbackQuery, storage: BotStorage):
    if not _is_admin(query.from_user.id):
        await query.answer("Нет доступа", show_alert=True)
        return
    lead_id = int(query.data.split(":")[1])
    await storage.set_lead_status(lead_id, "spam", query.from_user.id)
    await query.answer("Помечено как спам")
    await query.message.edit_text(f"{query.message.text}\n\n🚫 Спам")
