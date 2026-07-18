"""Форматирование сводки брифа и детект явного подтверждения клиентом."""
from __future__ import annotations

import re

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
