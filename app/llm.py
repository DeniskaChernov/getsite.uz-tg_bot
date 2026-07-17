"""LLM-слой: очередь 1 запрос/пользователь, таймаут 30 сек, выходной фильтр.

Модель отвечает только текстом; никаких инструментов с побочными эффектами.
Передача лида — детерминированный код (leads.py) по извлечённому состоянию брифа.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from openai import AsyncOpenAI

from app.config import config
from app.filters import output_violation, polish_reply
from app.prompt import BRIEF_EXTRACTOR_PROMPT, build_system_prompt

log = logging.getLogger(__name__)

LLM_TIMEOUT = 30
MAX_INPUT_CHARS = 2000
HISTORY_LIMIT = 20

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.llm_api_key, base_url=config.llm_base_url)
    return _client

# Не более одного параллельного LLM-запроса на пользователя
_user_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


class LLMBusy(Exception):
    """Уже идёт запрос этого пользователя."""


class LLMFiltered(Exception):
    """Ответ модели заблокирован выходным фильтром."""

    def __init__(self, reason: str):
        self.reason = reason


async def generate_reply(user_id: int, history: list[dict[str, str]],
                         service_name: str | None, lang: str, brief_state: str) -> str:
    lock = _user_locks[user_id]
    if lock.locked():
        raise LLMBusy
    async with lock:
        system = build_system_prompt(service_name, lang, brief_state)
        messages = [{"role": "system", "content": system}, *history[-HISTORY_LIMIT:]]
        resp = await asyncio.wait_for(
            _get_client().chat.completions.create(
                model=config.llm_model,
                messages=messages,
                max_tokens=600,
                temperature=0.7,
            ),
            timeout=LLM_TIMEOUT,
        )
        text = polish_reply((resp.choices[0].message.content or "").strip())
        reason = output_violation(text)
        if reason:
            log.error("Output filter hit: %s (user %s)", reason, user_id)
            raise LLMFiltered(reason)
        return text


_BRIEF_KEYS = ("service", "niche", "deadline", "budget_hint", "contact", "links", "summary")
# Бриф считается собранным, когда есть суть, услуга и ниша + срок или бюджет
_REQUIRED = ("service", "niche", "summary")


async def extract_brief(history: list[dict[str, str]]) -> dict[str, str]:
    """Отдельный дешёвый вызов: извлечь поля брифа из диалога. Ошибки не критичны."""
    dialog = "\n".join(f"{m['role']}: {m['content'][:500]}" for m in history[-HISTORY_LIMIT:])
    try:
        resp = await asyncio.wait_for(
            _get_client().chat.completions.create(
                model=config.llm_model,
                messages=[
                    {"role": "system", "content": BRIEF_EXTRACTOR_PROMPT},
                    {"role": "user", "content": dialog},
                ],
                max_tokens=400,
                temperature=0,
                response_format={"type": "json_object"},
            ),
            timeout=LLM_TIMEOUT,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        return {k: str(data.get(k, "") or "").strip() for k in _BRIEF_KEYS}
    except Exception:
        log.warning("Brief extraction failed", exc_info=True)
        return {}


def brief_is_complete(brief: dict[str, str]) -> bool:
    if not brief:
        return False
    if not all(brief.get(k) for k in _REQUIRED):
        return False
    return bool(brief.get("deadline") or brief.get("budget_hint"))
