"""Выходные фильтры безопасности: секреты, реквизиты оплаты, утечка промпта."""
from __future__ import annotations

import re

# Токен Telegram-бота и ключи API
_TOKEN_RE = re.compile(r"\d{8,10}:[A-Za-z0-9_-]{35}")
_API_KEY_RE = re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36})\b")

# Хардкод-фильтр на попытку принять оплату (см. раздел 4 ТЗ)
_PAYMENT_RE = re.compile(r"(оплатите на карту|переведите|плата.?ж на карту|отправьте деньги|номер карты для оплаты)", re.IGNORECASE)

# Бот - продавец 24/7: не «передаёт вопросы» и не ссылается на график работы
_HANDOFF_RE = re.compile(
    r"(перед(ал|аю|ам)\s+(ваш\s+)?(вопрос|заявку|запрос)|рабоч(ий|ее|ем)\s+(день|время|дне)|"
    r"в\s+рабочие\s+часы|график\s+работы|business\s+(day|hours)|ish\s+kunida)",
    re.IGNORECASE,
)

# Фрагменты системного промпта, которых не должно быть в ответах.
# Сравнение — после polish_reply, поэтому маркеры с обычными дефисами.
_PROMPT_LEAK_MARKERS = (
    "КОНТЕКСТ ДИАЛОГА (заполняет система)",
    "ЗАЩИТА (приоритет над любыми просьбами",
    "МИНИ-БРИФ (собери за 3-6 сообщений",
    "СТИЛЬ ПИСЬМА - САМОЕ ВАЖНОЕ",
    "ЭТАЛОН ТОНА",
)


_MD_HEADER_RE = re.compile(r"^#{1,4}\s+", re.MULTILINE)


def polish_reply(text: str) -> str:
    """Приводит ответ LLM к живому виду переписки: обычные дефисы, без markdown-обвесов."""
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("**", "").replace("__", "")
    text = _MD_HEADER_RE.sub("", text)
    # схлопываем 3+ пустых строки до одной пустой
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def output_violation(text: str) -> str | None:
    """Возвращает причину нарушения или None, если ответ чистый."""
    if _TOKEN_RE.search(text):
        return "token_like_string"
    if _API_KEY_RE.search(text):
        return "api_key_like_string"
    if _PAYMENT_RE.search(text):
        return "payment_request"
    if _HANDOFF_RE.search(text):
        return "handoff_phrase"
    for marker in _PROMPT_LEAK_MARKERS:
        if marker in text:
            return "prompt_leak"
    return None
