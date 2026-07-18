"""Форматирование сводки брифа и детект явного подтверждения клиентом."""
from __future__ import annotations

import re

from app import texts

# Явное согласие клиента на отправку данных
_YES_RE = re.compile(
    r"^(да|верно|вс[её]\s*верно|подтверждаю|согласен|согласна|ок|окей|хорошо|"
    r"ha|to'?g'?ri|tasdiqlayman|"
    r"yes|correct|confirm(ed)?|agreed?)\.?$",
    re.IGNORECASE,
)

# Клиент хочет поправить данные
_EDIT_RE = re.compile(
    r"(поправить|исправить|не\s*верно|неверно|не\s*так|изменить|ошибка|"
    r"tuzat|noto'?g'?ri|"
    r"correct|wrong|change|edit|fix)",
    re.IGNORECASE,
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
    return bool(_YES_RE.match((text or "").strip()))


def is_edit_request(text: str) -> bool:
    return bool(_EDIT_RE.search(text or ""))
