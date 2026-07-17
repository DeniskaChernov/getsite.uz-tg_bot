"""Карточка лида в админ-группу. Отправка — только детерминированный код."""
from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import config
from app.services import resolve_payload
from app.storage import BotStorage

log = logging.getLogger(__name__)


def _esc(value: str | None) -> str:
    return html.escape(str(value) if value else "-")


async def send_lead(bot: Bot, storage: BotStorage, user_id: int) -> int | None:
    user = await storage.get_user(user_id)
    if not user:
        return None
    brief = await storage.get_brief(user_id)
    payload = user.get("payload")
    service = brief.get("service") or resolve_payload(payload).name_ru
    summary = brief.get("summary") or "—"

    lead_id = await storage.create_lead(user_id, payload, summary)

    msg_count = await storage.message_count(user_id)
    started = await storage.first_message_at(user_id)
    started_str = (
        datetime.fromtimestamp(started, tz=timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        if started else "—"
    )

    card = (
        f"🟢 Новый лид #{lead_id}\n"
        f"Услуга: {_esc(service)} (payload: {_esc(payload)})\n"
        f"Клиент: {_esc(user.get('name') or user.get('first_name'))} @{_esc(user.get('username'))} "
        f"(id {user_id}), язык {_esc(user.get('lang'))}\n"
        f"Телефон: {_esc(user.get('phone'))}\n"
        f"Ниша: {_esc(brief.get('niche'))}\n"
        f"Срок: {_esc(brief.get('deadline'))}\n"
        f"Бюджет: {_esc(brief.get('budget_hint'))}\n"
        f"Ссылки: {_esc(brief.get('links'))}\n"
        f"Суть: {_esc(summary)}\n"
        f"Диалог: {msg_count} сообщений, начат {started_str}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Взял в работу", callback_data=f"lead_take:{lead_id}"),
        InlineKeyboardButton(text="Спам", callback_data=f"lead_spam:{lead_id}"),
    ]])
    try:
        await bot.send_message(config.admin_chat_id, card, reply_markup=kb)
        await storage.log_event("lead_sent", user_id, str(lead_id))
    except Exception:
        log.error("Failed to send lead #%s to admin group", lead_id, exc_info=True)
    return lead_id
