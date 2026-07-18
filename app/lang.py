"""Язык и письменность: RU / UZ / EN, латиница, кириллица, транслит в любом виде."""
from __future__ import annotations

import re
import unicodedata

Lang = str  # "ru" | "uz" | "en"

# Узбекская кириллица / типичные маркеры
_UZ_CYR = re.compile(
    r"[ўғҳқЎҒҲҚ]|(\b(салом|раҳмат|керак|қандай|билан|учун|лояҳа|нарх|муддат|"
    r"ассалому|алайкум|хизмат|сўм|минг)\b)",
    re.I,
)
_UZ_LAT = re.compile(
    r"\b(salom|rahmat|kerak|qanday|bilan|uchun|narx|muddat|loyiha|iltimos|"
    r"assalomu|alaykum|xizmat|so'?m|kerakmi|yo'?q|"
    r"qancha|turadi|qilish|ishlab|bering|yozing|xohlayman|mumkin)\b",
    re.I,
)
# Слабые маркеры (общие с RU/EN) - только вместе с сильным сигналом
_UZ_LAT_WEAK = re.compile(r"\b(sayt|bot|ha|xa|ming|mln|bor)\b", re.I)
_EN = re.compile(
    r"\b(the|and|for|with|please|need|want|website|price|how|much|what|hello|thanks|"
    r"landing|shop|bot|timeline|budget|estimate|quote|project|business)\b",
    re.I,
)
# Русский транслит латиницей (без общих слов sayt/bot/landing - они неоднозначны)
_RU_TRANSLIT = re.compile(
    r"\b(privet|zdravstvuj(te)?|skolko|stoit|nuzhen|nuzhna|nuzhno|magazin|"
    r"srok|dorogo|deshevo|spasibo|pozhalujsta|hocu|xochu|hochu|"
    r"korporativ|katalog|skidka|byudzhet|byudjet|svyaz|svjaz|pozvonite|"
    r"verno|podtverzhdayu|pozhalusta)\b",
    re.I,
)
_CYR_BLOCK = re.compile(r"[а-яёА-ЯЁўғҳқЎҒҲҚ]")
_LAT_BLOCK = re.compile(r"[a-zA-Z]")
# Частые «клавиатурные» опечатки / смешанный набор
_MIXED_HINT = re.compile(r"[a-zA-Z].*[а-яёА-ЯЁ]|[а-яёА-ЯЁ].*[a-zA-Z]")


def normalize_lang(code: str | None) -> Lang:
    if not code:
        return "ru"
    code = code.lower().strip()
    if code.startswith("uz"):
        return "uz"
    if code.startswith("en"):
        return "en"
    return "ru"


def fold_text(text: str | None) -> str:
    """Сглаживание для матчинга: NFKC, ё→е, ’→', нижний регистр, схлоп пробелов."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text).strip().lower()
    t = t.replace("ё", "е").replace("’", "'").replace("`", "'").replace("ʻ", "'").replace("ʼ", "'")
    t = re.sub(r"\s+", " ", t)
    return t


def detect_lang_from_text(text: str | None, fallback: Lang = "ru") -> Lang:
    """Грубая эвристика по содержимому - не меняет язык пользователя сама, только подсказка."""
    if not text or len(text.strip()) < 2:
        return fallback
    t = text.strip()
    scores = {"ru": 0, "uz": 0, "en": 0}
    uz_strong = bool(_UZ_CYR.search(t) or _UZ_LAT.search(t))
    if uz_strong:
        scores["uz"] += 3
    elif _UZ_LAT_WEAK.search(t):
        scores["uz"] += 1
    if _EN.search(t):
        scores["en"] += 2
    if _RU_TRANSLIT.search(t):
        scores["ru"] += 3
    if _CYR_BLOCK.search(t) and not _UZ_CYR.search(t):
        scores["ru"] += 2
    if _LAT_BLOCK.search(t) and not uz_strong and not _RU_TRANSLIT.search(t) and _EN.search(t):
        scores["en"] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return fallback
    # При ничьей предпочитаем более специфичный сигнал: uz > en > ru
    tied = [k for k, v in scores.items() if v == scores[best]]
    if len(tied) > 1:
        for pref in ("uz", "en", "ru"):
            if pref in tied:
                return pref  # type: ignore[return-value]
    return best  # type: ignore[return-value]


def script_hint(text: str | None) -> str:
    """Короткая подсказка модели о письменности клиента."""
    if not text:
        return "не определено"
    t = text.strip()
    has_cyr = bool(_CYR_BLOCK.search(t))
    has_lat = bool(_LAT_BLOCK.search(t))
    parts: list[str] = []
    if has_cyr and has_lat:
        parts.append("смесь латиницы и кириллицы")
    elif has_cyr:
        parts.append("кириллица")
    elif has_lat:
        parts.append("латиница")
    if _RU_TRANSLIT.search(t):
        parts.append("похоже на русский транслит латиницей")
    if _UZ_CYR.search(t):
        parts.append("узбекский (кириллица)")
    elif _UZ_LAT.search(t):
        parts.append("узбекский (латиница)")
    if _MIXED_HINT.search(t):
        parts.append("возможны опечатки при смене раскладки")
    return ", ".join(parts) if parts else "обычный текст"


def lang_label(lang: Lang) -> str:
    return {
        "ru": "русский (кириллица или транслит латиницей - оба понимай)",
        "uz": "o'zbekcha (lotin yoki kirill - ikkalasini ham tushun)",
        "en": "English",
    }.get(normalize_lang(lang), "русский")
