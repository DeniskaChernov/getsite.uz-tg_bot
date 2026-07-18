"""Извлечение и сохранение референс-ссылок клиента в бриф."""
from __future__ import annotations

import re
from typing import Any

from aiogram.types import Message

from app.storage import BotStorage

_URL_RE = re.compile(r"https?://[^\s<>\"\]\)\,]+", re.IGNORECASE)


def extract_urls_from_text(text: str | None) -> list[str]:
    if not text:
        return []
    found = []
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(".,);]")
        if url not in found:
            found.append(url)
    return found


def extract_urls_from_message(message: Message) -> list[str]:
    urls = extract_urls_from_text(message.text or message.caption)
    for ent in message.entities or message.caption_entities or []:
        if ent.type == "url" and message.text:
            chunk = message.text[ent.offset: ent.offset + ent.length]
            if chunk and chunk not in urls:
                urls.append(chunk)
        elif ent.type == "text_link" and ent.url and ent.url not in urls:
            urls.append(ent.url)
    return urls


async def merge_links_into_brief(storage: BotStorage, user_id: int, urls: list[str]) -> list[str]:
    """Добавляет новые URL в brief.links. Возвращает реально добавленные."""
    if not urls:
        return []
    brief: dict[str, Any] = await storage.get_brief(user_id)
    existing_raw = (brief.get("links") or "").strip()
    existing = [x.strip() for x in re.split(r"[\s,;]+", existing_raw) if x.strip()]
    added = []
    for url in urls:
        if url not in existing:
            existing.append(url)
            added.append(url)
    if added:
        brief["links"] = " ".join(existing)
        await storage.save_brief(user_id, brief)
    return added


async def note_media_in_brief(storage: BotStorage, user_id: int, kind: str) -> None:
    brief = await storage.get_brief(user_id)
    notes = brief.get("_media_notes") or []
    if not isinstance(notes, list):
        notes = []
    notes.append(kind)
    brief["_media_notes"] = notes[-10:]  # не раздуваем
    # для менеджера в snapshot/карточке - человекочитаемая пометка в links
    marker = f"[{kind}]"
    links = (brief.get("links") or "").strip()
    if marker not in links:
        brief["links"] = f"{links} {marker}".strip() if links else marker
    await storage.save_brief(user_id, brief)
