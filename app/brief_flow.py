"""Форматирование сводки брифа и детект явного подтверждения клиентом."""
from __future__ import annotations

import re

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app import texts
from app.lang import fold_text

# Явное согласие (после fold_text): RU / UZ лат+кир / EN / транслит
_YES_RE = re.compile(
    r"^(да+|даа|верно|все\s*верно|всё\s*верно|подтверждаю|подтверждаю\s*все|"
    r"да,?\s*подтверждаю|согласен|согласна|ок|окей|хорошо|ага|угу|"
    r"da+|daa|verno|vse\s*verno|podtverzhdayu|soglasen|soglasna|ok|okay|alright|"
    r"ha+|xaa|ҳа+|ха+|xa+|to'?g'?ri|togri|tasdiqlayman|ha,?\s*tasdiqlayman|"
    r"roziman|bo'?ldi|boldi|"
    r"yes+|yep|yeah|correct|confirm(ed)?|agreed?|sure|all\s*right|"
    r"yes,?\s*i\s*confirm)\.?$"
)

# Клиент хочет поправить данные
_EDIT_RE = re.compile(
    r"(поправить|исправить|не\s*верно|неверно|не\s*так|изменить|ошибка|нет|"
    r"popravit|ispravit|ne\s*verno|neverno|net|"
    r"tuzat|noto'?g'?ri|notogri|yo'?q|yoq|"
    r"correct|wrong|change|edit|fix|no\b)",
)


def contact_from_user(user: dict | None) -> str:
    """Контактная строка из профиля регистрации."""
    if not user:
        return ""
    parts: list[str] = []
    name = (user.get("name") or user.get("first_name") or "").strip()
    if name:
        parts.append(name)
    phone = (user.get("phone") or "").strip()
    if phone:
        parts.append(phone)
    username = (user.get("username") or "").strip()
    if username:
        parts.append("@" + username.lstrip("@"))
    return ", ".join(parts)


def ensure_brief_contact(brief: dict, user: dict | None) -> dict:
    """Если extractor не дал контакт - подставляем из регистрации."""
    if (brief.get("contact") or "").strip():
        return brief
    filled = contact_from_user(user)
    if filled:
        brief = {**brief, "contact": filled}
    return brief


def confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.CONFIRM_YES_BTN[lang], callback_data="brief_yes")],
        [InlineKeyboardButton(text=texts.CONFIRM_EDIT_BTN[lang], callback_data="brief_edit")],
    ])


def format_brief_summary(brief: dict, lang: str) -> str:
    labels = texts.BRIEF_FIELD_LABELS.get(lang) or texts.BRIEF_FIELD_LABELS["ru"]
    lines = [texts.BRIEF_SUMMARY_HEADER[lang], ""]
    for key in ("service", "niche", "deadline", "budget_hint", "contact", "links", "summary"):
        value = (brief.get(key) or "").strip()
        if value and not key.startswith("_"):
            lines.append(f"{labels[key]}: {value}")
    lines.append("")
    lines.append(texts.BRIEF_SUMMARY_ASK[lang])
    return "\n".join(lines)


def is_confirmation(text: str) -> bool:
    return bool(_YES_RE.match(fold_text(text)))


def is_edit_request(text: str) -> bool:
    return bool(_EDIT_RE.search(fold_text(text)))
