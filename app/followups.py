"""Мягкие follow-up сообщения, если клиент замолчал после ответа бота.

Telegram разрешает писать первым, если клиент уже нажал /start.
Расписание: 1-е через 6ч тишины, 2-е через 24ч после 1-го, 3-е через 48ч после 2-го.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from app.brief_flow import confirm_keyboard
from app import texts
from app.storage import BotStorage

log = logging.getLogger(__name__)

# Интервалы до следующего напоминания (по номеру: 0 → 6ч, 1 → 24ч, 2 → 48ч)
FOLLOWUP_GAPS_SEC = (6 * 3600, 24 * 3600, 48 * 3600)
MAX_FOLLOWUPS = len(FOLLOWUP_GAPS_SEC)
# Как часто проверять кандидатов
FOLLOWUP_POLL_SEC = 15 * 60


def followup_text(lang: str, name: str | None, awaiting_confirm: bool, n: int) -> str:
    who = (name or "").strip()
    name_part = f", {who}" if who else ""
    if awaiting_confirm:
        templates = texts.FOLLOWUP_CONFIRM
    elif n == 0:
        templates = texts.FOLLOWUP_FIRST
    elif n == 1:
        templates = texts.FOLLOWUP_SECOND
    else:
        templates = texts.FOLLOWUP_THIRD
    msg = templates.get(lang) or templates["ru"]
    return msg.format(name_part=name_part)


async def run_followups_once(bot: Bot, storage: BotStorage) -> int:
    candidates = await storage.list_followup_candidates(FOLLOWUP_GAPS_SEC)
    sent = 0
    for c in candidates:
        lang = c["lang"] if c["lang"] in ("ru", "uz", "en") else "ru"
        text = followup_text(lang, c.get("name"), c["awaiting_confirm"], c["followup_count"])
        kb = confirm_keyboard(lang) if c["awaiting_confirm"] else None
        try:
            await bot.send_message(c["user_id"], text, reply_markup=kb)
            await storage.add_message(c["user_id"], "assistant", text)
            await storage.mark_followup_sent(c["user_id"])
            await storage.log_event("followup", c["user_id"], str(c["followup_count"] + 1))
            sent += 1
            await asyncio.sleep(0.05)  # мягкий троттлинг Telegram
        except (TelegramForbiddenError, TelegramBadRequest):
            log.info("Follow-up skipped for user %s (blocked or bad chat)", c["user_id"])
        except Exception:
            log.error("Follow-up failed for user %s", c["user_id"], exc_info=True)
    return sent


async def followup_loop(bot: Bot, storage: BotStorage) -> None:
    await asyncio.sleep(60)  # дать сервису подняться
    while True:
        try:
            n = await run_followups_once(bot, storage)
            if n:
                log.info("Follow-ups sent: %s", n)
        except Exception:
            log.error("Follow-up loop error", exc_info=True)
        await asyncio.sleep(FOLLOWUP_POLL_SEC)
