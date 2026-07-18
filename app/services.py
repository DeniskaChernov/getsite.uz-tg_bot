"""Каталог услуг и deep-link payload'ов. Payload — данные, не команда."""
from __future__ import annotations

import re
from dataclasses import dataclass

PAYLOAD_RE = re.compile(r"^[a-z0-9_]{1,64}$")


@dataclass(frozen=True)
class Service:
    payload: str
    name_ru: str
    name_uz: str
    name_en: str
    price_ru: str  # ориентир «от», уже отформатирован
    price_uz: str
    price_en: str


SERVICES: dict[str, Service] = {
    s.payload: s
    for s in [
        Service("discuss", "Обсудить проект", "Loyihani muhokama qilish", "Discuss a project", "", "", ""),
        Service("sites_landing", "Лендинг", "Landing sahifa", "Landing page",
                "от 4,9 млн сум", "4,9 mln so'mdan", "from 4.9M UZS"),
        Service("sites_corporate", "Корпоративный сайт", "Korporativ sayt", "Corporate website",
                "от 8,9 млн сум", "8,9 mln so'mdan", "from 8.9M UZS"),
        Service("sites_catalog", "Сайт-каталог", "Katalog-sayt", "Catalog website",
                "от 11,9 млн сум", "11,9 mln so'mdan", "from 11.9M UZS"),
        Service("sites_shop", "Интернет-магазин", "Internet-do'kon", "Online store",
                "от 14,9 млн сум", "14,9 mln so'mdan", "from 14.9M UZS"),
        Service("tg_bot", "Telegram-бот", "Telegram-bot", "Telegram bot",
                "от 4,5 млн сум", "4,5 mln so'mdan", "from 4.5M UZS"),
        Service("tg_admin", "Бот + админ-панель", "Bot + admin-panel", "Bot + admin panel",
                "от 9,9 млн сум", "9,9 mln so'mdan", "from 9.9M UZS"),
        Service("tg_miniapp", "Telegram Mini App", "Telegram Mini App", "Telegram Mini App",
                "от 18 млн сум", "18 mln so'mdan", "from 18M UZS"),
        Service("auto_analytics", "Аналитика и проектирование", "Tahlil va loyihalash", "Analytics & design",
                "от 1,9 млн сум", "1,9 mln so'mdan", "from 1.9M UZS"),
        Service("auto_process", "Автоматизация процесса", "Jarayonni avtomatlashtirish", "Process automation",
                "от 3 млн сум", "3 mln so'mdan", "from 3M UZS"),
        Service("auto_integration", "Интеграция систем", "Tizimlarni integratsiya qilish", "Systems integration",
                "от 2,5 млн сум", "2,5 mln so'mdan", "from 2.5M UZS"),
        Service("auto_internal", "Внутренняя бизнес-система", "Ichki biznes-tizim", "Internal business system",
                "от 20 млн сум", "20 mln so'mdan", "from 20M UZS"),
        Service("auto_crm", "CRM с нуля", "Noldan CRM", "Custom CRM",
                "от 25 млн сум", "25 mln so'mdan", "from 25M UZS"),
        Service("support_maint", "Техническое сопровождение", "Texnik qo'llab-quvvatlash", "Technical support",
                "от 700 тыс сум/мес", "oyiga 700 ming so'mdan", "from 700K UZS/mo"),
    ]
}


def resolve_payload(raw: str | None) -> Service:
    """Мусорный или пустой payload → discuss."""
    if raw and PAYLOAD_RE.match(raw) and raw in SERVICES:
        return SERVICES[raw]
    return SERVICES["discuss"]
