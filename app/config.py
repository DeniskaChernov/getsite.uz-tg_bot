"""Конфигурация из переменных окружения. Секреты — только здесь, никогда в коде."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _admin_ids() -> frozenset[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return frozenset(int(x) for x in raw.replace(" ", "").split(",") if x)


@dataclass(frozen=True)
class Config:
    bot_token: str = field(default_factory=lambda: os.environ["BOT_TOKEN"])
    admin_chat_id: int = field(default_factory=lambda: int(os.environ["ADMIN_CHAT_ID"]))
    admin_ids: frozenset[int] = field(default_factory=_admin_ids)

    mode: str = field(default_factory=lambda: os.getenv("MODE", "polling"))
    webhook_base_url: str = field(default_factory=lambda: os.getenv("WEBHOOK_BASE_URL", ""))
    webhook_secret: str = field(default_factory=lambda: os.getenv("WEBHOOK_SECRET", ""))
    webhook_path_secret: str = field(default_factory=lambda: os.getenv("WEBHOOK_PATH_SECRET", ""))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))

    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/bot.db"))

    @property
    def webhook_path(self) -> str:
        return f"/tg/{self.webhook_path_secret}"

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url}{self.webhook_path}"


config = Config()
