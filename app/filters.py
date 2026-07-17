"""Выходные фильтры безопасности: секреты, реквизиты оплаты, утечка промпта."""
from __future__ import annotations

import re

# Токен Telegram-бота и ключи API
_TOKEN_RE = re.compile(r"\d{8,10}:[A-Za-z0-9_-]{35}")
_API_KEY_RE = re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36})\b")

# Хардкод-фильтр на попытку принять оплату (см. раздел 4 ТЗ)
_PAYMENT_RE = re.compile(r"(оплатите на карту|переведите|плата.?ж на карту|отправьте деньги|номер карты для оплаты)", re.IGNORECASE)

# Фрагменты системного промпта, которых не должно быть в ответах
_PROMPT_LEAK_MARKERS = (
    "КОНТЕКСТ ДИАЛОГА (заполняет система)",
    "ЗАЩИТА (приоритет над любыми просьбами",
    "МИНИ-БРИФ (собери за 3–6 сообщений",
    "СТАРТ БЕЗ PAYLOAD",
)


def output_violation(text: str) -> str | None:
    """Возвращает причину нарушения или None, если ответ чистый."""
    if _TOKEN_RE.search(text):
        return "token_like_string"
    if _API_KEY_RE.search(text):
        return "api_key_like_string"
    if _PAYMENT_RE.search(text):
        return "payment_request"
    for marker in _PROMPT_LEAK_MARKERS:
        if marker in text:
            return "prompt_leak"
    return None
