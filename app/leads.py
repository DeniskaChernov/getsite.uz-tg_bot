"""Карточка лида в админ-группу. Отправка - только детерминированный код."""
from __future__ import annotations

import html
import json
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


def build_lead_snapshot(user: dict, brief: dict, msg_count: int, started_at: int | None) -> str:
    """Полный снимок заявки для bot_leads.snapshot (JSON) - удобно для CRM позже."""
    public_brief = {k: v for k, v in brief.items() if v and not str(k).startswith("_")}
    return json.dumps(
        {
            "user": {
                "user_id": user.get("user_id"),
                "name": user.get("name") or user.get("first_name"),
                "username": user.get("username"),
                "phone": user.get("phone"),
                "lang": user.get("lang"),
                "payload": user.get("payload"),
            },
            "brief": public_brief,
            "dialog": {"message_count": msg_count, "started_at": started_at},
        },
        ensure_ascii=False,
    )


async def send_lead(bot: Bot, storage: BotStorage, user_id: int) -> int | None:
    user = await storage.get_user(user_id)
    if not user:
        return None
    brief = await storage.get_brief(user_id)
    payload = user.get("payload")
    service = brief.get("service") or resolve_payload(payload).name_ru
    summary = brief.get("summary") or "-"

    msg_count = await storage.message_count(user_id)
    started = await storage.first_message_at(user_id)
    snapshot = build_lead_snapshot(user, brief, msg_count, started)
    lead_id = await storage.create_lead(user_id, payload, summary, snapshot=snapshot)

    started_str = (
        datetime.fromtimestamp(started, tz=timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        if started else "-"
    )

    contact_line = brief.get("contact") or "-"
    card = (
        f"🟢 Новый лид #{lead_id}\n"
        f"Услуга: {_esc(service)} (payload: {_esc(payload)})\n"
        f"Клиент: {_esc(user.get('name') or user.get('first_name'))} @{_esc(user.get('username'))} "
        f"(id {user_id}), язык {_esc(user.get('lang'))}\n"
        f"Телефон: {_esc(user.get('phone'))}\n"
        f"Контакт из брифа: {_esc(contact_line)}\n"
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
        await bot.send_message(config.admin_chat_id, card, reply_markup=kb, parse_mode="HTML")
        await storage.log_event("lead_sent", user_id, str(lead_id))
        return lead_id
    except Exception:
        log.error("Failed to send lead #%s to admin group", lead_id, exc_info=True)
        return None
