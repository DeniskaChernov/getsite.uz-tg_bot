"""SQLite-хранилище: пользователи, история диалога, брифы, лиды, метрики."""
from __future__ import annotations

import json
import os
import time
from typing import Any

import aiosqlite

RETENTION_DAYS = 90

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    lang        TEXT NOT NULL DEFAULT 'ru',
    payload     TEXT,
    muted       INTEGER NOT NULL DEFAULT 0,
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    role        TEXT NOT NULL,             -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, id);

CREATE TABLE IF NOT EXISTS briefs (
    user_id     INTEGER PRIMARY KEY,
    data        TEXT NOT NULL DEFAULT '{}',   -- JSON: service, niche, deadline, budget, contact, links
    updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    payload     TEXT,
    summary     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new',  -- new | taken | spam
    taken_by    INTEGER,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    kind        TEXT NOT NULL,               -- start | brief_done | lead_sent | llm_error | filter_hit
    meta        TEXT,
    created_at  INTEGER NOT NULL
);
"""


class Storage:
    def __init__(self, db_path: str):
        self._path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "Storage not connected"
        return self._db

    # --- users ---

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None,
                          lang: str, payload: str | None = None) -> None:
        now = int(time.time())
        await self.db.execute(
            """INSERT INTO users (user_id, username, first_name, lang, payload, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 username=excluded.username, first_name=excluded.first_name,
                 payload=COALESCE(excluded.payload, users.payload), updated_at=excluded.updated_at""",
            (user_id, username, first_name, lang, payload, now, now),
        )
        await self.db.commit()

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        async with self.db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self.db.execute("UPDATE users SET lang=?, updated_at=? WHERE user_id=?",
                              (lang, int(time.time()), user_id))
        await self.db.commit()

    async def set_muted(self, user_id: int, muted: bool) -> None:
        await self.db.execute("UPDATE users SET muted=? WHERE user_id=?", (int(muted), user_id))
        await self.db.commit()

    # --- messages ---

    async def add_message(self, user_id: int, role: str, content: str) -> None:
        await self.db.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, int(time.time())),
        )
        await self.db.commit()

    async def history(self, user_id: int, limit: int = 20) -> list[dict[str, str]]:
        async with self.db.execute(
            "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    async def message_count(self, user_id: int) -> int:
        async with self.db.execute("SELECT COUNT(*) c FROM messages WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        return row["c"]

    async def first_message_at(self, user_id: int) -> int | None:
        async with self.db.execute(
            "SELECT MIN(created_at) t FROM messages WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return row["t"]

    # --- briefs ---

    async def get_brief(self, user_id: int) -> dict[str, Any]:
        async with self.db.execute("SELECT data FROM briefs WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        return json.loads(row["data"]) if row else {}

    async def save_brief(self, user_id: int, data: dict[str, Any]) -> None:
        await self.db.execute(
            """INSERT INTO briefs (user_id, data, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at""",
            (user_id, json.dumps(data, ensure_ascii=False), int(time.time())),
        )
        await self.db.commit()

    # --- leads ---

    async def create_lead(self, user_id: int, payload: str | None, summary: str) -> int:
        cur = await self.db.execute(
            "INSERT INTO leads (user_id, payload, summary, created_at) VALUES (?, ?, ?, ?)",
            (user_id, payload, summary, int(time.time())),
        )
        await self.db.commit()
        return cur.lastrowid

    async def set_lead_status(self, lead_id: int, status: str, taken_by: int | None = None) -> None:
        await self.db.execute("UPDATE leads SET status=?, taken_by=? WHERE id=?",
                              (status, taken_by, lead_id))
        await self.db.commit()

    async def recent_leads(self, limit: int = 10) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    # --- events / stats ---

    async def log_event(self, kind: str, user_id: int | None = None, meta: str | None = None) -> None:
        await self.db.execute(
            "INSERT INTO events (user_id, kind, meta, created_at) VALUES (?, ?, ?, ?)",
            (user_id, kind, meta, int(time.time())),
        )
        await self.db.commit()

    async def stats(self, days: int = 7) -> dict[str, Any]:
        since = int(time.time()) - days * 86400
        out: dict[str, Any] = {}
        async with self.db.execute(
            "SELECT kind, COUNT(*) c FROM events WHERE created_at>=? GROUP BY kind", (since,)
        ) as cur:
            out["events"] = {r["kind"]: r["c"] for r in await cur.fetchall()}
        async with self.db.execute(
            "SELECT COALESCE(meta,'?') p, COUNT(*) c FROM events WHERE kind='start' AND created_at>=? GROUP BY meta",
            (since,),
        ) as cur:
            out["starts_by_payload"] = {r["p"]: r["c"] for r in await cur.fetchall()}
        async with self.db.execute(
            "SELECT COUNT(*) c FROM leads WHERE created_at>=?", (since,)
        ) as cur:
            out["leads"] = (await cur.fetchone())["c"]
        return out

    # --- privacy ---

    async def forget_user(self, user_id: int) -> None:
        for table in ("messages", "briefs", "leads", "events", "users"):
            await self.db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        await self.db.commit()

    async def purge_old_history(self) -> int:
        """Удаление истории старше RETENTION_DAYS (запускается раз в сутки)."""
        cutoff = int(time.time()) - RETENTION_DAYS * 86400
        cur = await self.db.execute("DELETE FROM messages WHERE created_at<?", (cutoff,))
        await self.db.commit()
        return cur.rowcount
