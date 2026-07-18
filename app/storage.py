"""Хранилище клиентов, диалогов, брифов и лидов.

Две реализации с одинаковым интерфейсом:
- PgStorage (asyncpg) — продакшен, общая Postgres с сайтом (таблицы с префиксом bot_)
- SqliteStorage (aiosqlite) — локальная разработка и тесты

Выбор — фабрикой create_storage() по наличию DATABASE_URL.

Регистрация клиента (reg_state): need_lang → need_name → need_phone → done.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Protocol

RETENTION_DAYS = 90

REG_NEED_LANG = "need_lang"
REG_NEED_NAME = "need_name"
REG_NEED_PHONE = "need_phone"
REG_DONE = "done"


class BotStorage(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None,
                          lang: str, payload: str | None = None) -> None: ...
    async def get_user(self, user_id: int) -> dict[str, Any] | None: ...
    async def set_lang(self, user_id: int, lang: str) -> None: ...
    async def set_name(self, user_id: int, name: str) -> None: ...
    async def set_phone(self, user_id: int, phone: str | None) -> None: ...
    async def set_reg_state(self, user_id: int, state: str) -> None: ...
    async def set_muted(self, user_id: int, muted: bool) -> None: ...
    async def add_message(self, user_id: int, role: str, content: str) -> None: ...
    async def history(self, user_id: int, limit: int = 20) -> list[dict[str, str]]: ...
    async def message_count(self, user_id: int) -> int: ...
    async def first_message_at(self, user_id: int) -> int | None: ...
    async def get_brief(self, user_id: int) -> dict[str, Any]: ...
    async def save_brief(self, user_id: int, data: dict[str, Any]) -> None: ...
    async def create_lead(self, user_id: int, payload: str | None, summary: str) -> int: ...
    async def set_lead_status(self, lead_id: int, status: str, taken_by: int | None = None) -> None: ...
    async def recent_leads(self, limit: int = 10) -> list[dict[str, Any]]: ...
    async def log_event(self, kind: str, user_id: int | None = None, meta: str | None = None) -> None: ...
    async def stats(self, days: int = 7) -> dict[str, Any]: ...
    async def forget_user(self, user_id: int) -> None: ...
    async def purge_old_history(self) -> int: ...
    async def claim_lead(self, user_id: int) -> bool: ...
    async def reset_lead_flags(self, user_id: int) -> None: ...
    async def list_followup_candidates(self, silent_after_sec: int, max_followups: int = 2) -> list[dict]: ...
    async def mark_followup_sent(self, user_id: int) -> None: ...


def create_storage() -> BotStorage:
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        return PgStorage(database_url)
    return SqliteStorage(os.getenv("DB_PATH", "data/bot.db"))


# ---------------------------------------------------------------------------
# PostgreSQL (продакшен, общая БД с сайтом → в перспективе CRM)
# ---------------------------------------------------------------------------

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_users (
    user_id     BIGINT PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    name        TEXT,
    phone       TEXT,
    lang        TEXT NOT NULL DEFAULT 'ru',
    payload     TEXT,
    reg_state   TEXT NOT NULL DEFAULT 'need_lang',
    muted       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  BIGINT NOT NULL,
    updated_at  BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_messages (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bot_messages_user ON bot_messages(user_id, id);

CREATE TABLE IF NOT EXISTS bot_briefs (
    user_id     BIGINT PRIMARY KEY,
    data        TEXT NOT NULL DEFAULT '{}',
    updated_at  BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_leads (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    payload     TEXT,
    summary     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new',
    taken_by    BIGINT,
    created_at  BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT,
    kind        TEXT NOT NULL,
    meta        TEXT,
    created_at  BIGINT NOT NULL
);
"""


class PgStorage:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool = None

    async def connect(self) -> None:
        import asyncpg
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(_PG_SCHEMA)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None,
                          lang: str, payload: str | None = None) -> None:
        now = int(time.time())
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO bot_users (user_id, username, first_name, lang, payload, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $6)
                   ON CONFLICT (user_id) DO UPDATE SET
                     username = EXCLUDED.username, first_name = EXCLUDED.first_name,
                     lang = EXCLUDED.lang,
                     payload = COALESCE(EXCLUDED.payload, bot_users.payload),
                     updated_at = EXCLUDED.updated_at""",
                user_id, username, first_name, lang, payload, now,
            )

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM bot_users WHERE user_id = $1", user_id)
        return dict(row) if row else None

    async def _set_field(self, user_id: int, field: str, value: Any) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE bot_users SET {field} = $1, updated_at = $2 WHERE user_id = $3",
                value, int(time.time()), user_id,
            )

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self._set_field(user_id, "lang", lang)

    async def set_name(self, user_id: int, name: str) -> None:
        await self._set_field(user_id, "name", name)

    async def set_phone(self, user_id: int, phone: str | None) -> None:
        await self._set_field(user_id, "phone", phone)

    async def set_reg_state(self, user_id: int, state: str) -> None:
        await self._set_field(user_id, "reg_state", state)

    async def set_muted(self, user_id: int, muted: bool) -> None:
        await self._set_field(user_id, "muted", muted)

    async def add_message(self, user_id: int, role: str, content: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO bot_messages (user_id, role, content, created_at) VALUES ($1, $2, $3, $4)",
                user_id, role, content, int(time.time()),
            )

    async def history(self, user_id: int, limit: int = 20) -> list[dict[str, str]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role, content FROM bot_messages WHERE user_id = $1 ORDER BY id DESC LIMIT $2",
                user_id, limit,
            )
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    async def message_count(self, user_id: int) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM bot_messages WHERE user_id = $1", user_id)

    async def first_message_at(self, user_id: int) -> int | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT MIN(created_at) FROM bot_messages WHERE user_id = $1", user_id)

    async def get_brief(self, user_id: int) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            data = await conn.fetchval("SELECT data FROM bot_briefs WHERE user_id = $1", user_id)
        return json.loads(data) if data else {}

    async def save_brief(self, user_id: int, data: dict[str, Any]) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO bot_briefs (user_id, data, updated_at) VALUES ($1, $2, $3)
                   ON CONFLICT (user_id) DO UPDATE SET data = EXCLUDED.data, updated_at = EXCLUDED.updated_at""",
                user_id, json.dumps(data, ensure_ascii=False), int(time.time()),
            )

    async def claim_lead(self, user_id: int) -> bool:
        """Атомарно помечает бриф как отправленный. True - мы первые, False - уже занято."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT data FROM bot_briefs WHERE user_id = $1 FOR UPDATE", user_id)
                data = json.loads(row["data"]) if row else {}
                if data.get("_lead_sent"):
                    return False
                data["_lead_sent"] = True
                data.pop("_awaiting_confirm", None)
                await conn.execute(
                    """INSERT INTO bot_briefs (user_id, data, updated_at) VALUES ($1, $2, $3)
                       ON CONFLICT (user_id) DO UPDATE SET data = EXCLUDED.data, updated_at = EXCLUDED.updated_at""",
                    user_id, json.dumps(data, ensure_ascii=False), int(time.time()),
                )
                return True

    async def reset_lead_flags(self, user_id: int) -> None:
        brief = await self.get_brief(user_id)
        if not brief:
            return
        brief.pop("_lead_sent", None)
        brief.pop("_awaiting_confirm", None)
        brief.pop("_followup_count", None)
        brief.pop("_last_followup_at", None)
        await self.save_brief(user_id, brief)

    async def create_lead(self, user_id: int, payload: str | None, summary: str) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "INSERT INTO bot_leads (user_id, payload, summary, created_at) VALUES ($1, $2, $3, $4) RETURNING id",
                user_id, payload, summary, int(time.time()),
            )

    async def set_lead_status(self, lead_id: int, status: str, taken_by: int | None = None) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE bot_leads SET status = $1, taken_by = $2 WHERE id = $3",
                status, taken_by, lead_id,
            )

    async def recent_leads(self, limit: int = 10) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM bot_leads ORDER BY id DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

    async def log_event(self, kind: str, user_id: int | None = None, meta: str | None = None) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO bot_events (user_id, kind, meta, created_at) VALUES ($1, $2, $3, $4)",
                user_id, kind, meta, int(time.time()),
            )

    async def stats(self, days: int = 7) -> dict[str, Any]:
        since = int(time.time()) - days * 86400
        out: dict[str, Any] = {}
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT kind, COUNT(*) c FROM bot_events WHERE created_at >= $1 GROUP BY kind", since)
            out["events"] = {r["kind"]: r["c"] for r in rows}
            rows = await conn.fetch(
                "SELECT COALESCE(meta, '?') p, COUNT(*) c FROM bot_events "
                "WHERE kind = 'start' AND created_at >= $1 GROUP BY meta", since)
            out["starts_by_payload"] = {r["p"]: r["c"] for r in rows}
            out["leads"] = await conn.fetchval(
                "SELECT COUNT(*) FROM bot_leads WHERE created_at >= $1", since)
        return out

    async def forget_user(self, user_id: int) -> None:
        async with self._pool.acquire() as conn:
            for table in ("bot_messages", "bot_briefs", "bot_leads", "bot_events", "bot_users"):
                await conn.execute(f"DELETE FROM {table} WHERE user_id = $1", user_id)

    async def list_followup_candidates(self, silent_after_sec: int, max_followups: int = 2) -> list[dict]:
        """Клиенты, у которых последнее сообщение - от бота, и тишина дольше silent_after_sec."""
        cutoff = int(time.time()) - silent_after_sec
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.user_id, u.lang, u.name, b.data AS brief_data, last.created_at AS last_at, last.role AS last_role
                FROM bot_users u
                JOIN LATERAL (
                    SELECT role, created_at FROM bot_messages
                    WHERE user_id = u.user_id ORDER BY id DESC LIMIT 1
                ) last ON TRUE
                LEFT JOIN bot_briefs b ON b.user_id = u.user_id
                WHERE u.reg_state = 'done' AND u.muted = FALSE
                  AND last.role = 'assistant' AND last.created_at <= $1
                """,
                cutoff,
            )
        out = []
        for r in rows:
            brief = json.loads(r["brief_data"]) if r["brief_data"] else {}
            if brief.get("_lead_sent"):
                continue
            count = int(brief.get("_followup_count") or 0)
            if count >= max_followups:
                continue
            last_fu = int(brief.get("_last_followup_at") or 0)
            # Второе напоминание - не раньше чем через 24ч после первого
            if count >= 1 and int(time.time()) - last_fu < 86400:
                continue
            out.append({
                "user_id": r["user_id"],
                "lang": r["lang"] or "ru",
                "name": r["name"],
                "brief": brief,
                "awaiting_confirm": bool(brief.get("_awaiting_confirm")),
                "followup_count": count,
            })
        return out

    async def mark_followup_sent(self, user_id: int) -> None:
        brief = await self.get_brief(user_id)
        brief["_followup_count"] = int(brief.get("_followup_count") or 0) + 1
        brief["_last_followup_at"] = int(time.time())
        await self.save_brief(user_id, brief)

    async def purge_old_history(self) -> int:
        cutoff = int(time.time()) - RETENTION_DAYS * 86400
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM bot_messages WHERE created_at < $1", cutoff)
        return int(result.split()[-1]) if result else 0


# ---------------------------------------------------------------------------
# SQLite (локальная разработка и тесты)
# ---------------------------------------------------------------------------

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    name        TEXT,
    phone       TEXT,
    lang        TEXT NOT NULL DEFAULT 'ru',
    payload     TEXT,
    reg_state   TEXT NOT NULL DEFAULT 'need_lang',
    muted       INTEGER NOT NULL DEFAULT 0,
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bot_messages_user ON bot_messages(user_id, id);

CREATE TABLE IF NOT EXISTS bot_briefs (
    user_id     INTEGER PRIMARY KEY,
    data        TEXT NOT NULL DEFAULT '{}',
    updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    payload     TEXT,
    summary     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new',
    taken_by    INTEGER,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    kind        TEXT NOT NULL,
    meta        TEXT,
    created_at  INTEGER NOT NULL
);
"""


class SqliteStorage:
    def __init__(self, db_path: str):
        self._path = db_path
        self._db = None

    async def connect(self) -> None:
        import aiosqlite
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SQLITE_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None,
                          lang: str, payload: str | None = None) -> None:
        now = int(time.time())
        await self._db.execute(
            """INSERT INTO bot_users (user_id, username, first_name, lang, payload, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 username=excluded.username, first_name=excluded.first_name,
                 lang=excluded.lang,
                 payload=COALESCE(excluded.payload, bot_users.payload), updated_at=excluded.updated_at""",
            (user_id, username, first_name, lang, payload, now, now),
        )
        await self._db.commit()

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        async with self._db.execute("SELECT * FROM bot_users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def _set_field(self, user_id: int, field: str, value: Any) -> None:
        await self._db.execute(
            f"UPDATE bot_users SET {field}=?, updated_at=? WHERE user_id=?",
            (value, int(time.time()), user_id),
        )
        await self._db.commit()

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self._set_field(user_id, "lang", lang)

    async def set_name(self, user_id: int, name: str) -> None:
        await self._set_field(user_id, "name", name)

    async def set_phone(self, user_id: int, phone: str | None) -> None:
        await self._set_field(user_id, "phone", phone)

    async def set_reg_state(self, user_id: int, state: str) -> None:
        await self._set_field(user_id, "reg_state", state)

    async def set_muted(self, user_id: int, muted: bool) -> None:
        await self._set_field(user_id, "muted", int(muted))

    async def add_message(self, user_id: int, role: str, content: str) -> None:
        await self._db.execute(
            "INSERT INTO bot_messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, int(time.time())),
        )
        await self._db.commit()

    async def history(self, user_id: int, limit: int = 20) -> list[dict[str, str]]:
        async with self._db.execute(
            "SELECT role, content FROM bot_messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    async def message_count(self, user_id: int) -> int:
        async with self._db.execute(
            "SELECT COUNT(*) c FROM bot_messages WHERE user_id=?", (user_id,)
        ) as cur:
            return (await cur.fetchone())["c"]

    async def first_message_at(self, user_id: int) -> int | None:
        async with self._db.execute(
            "SELECT MIN(created_at) t FROM bot_messages WHERE user_id=?", (user_id,)
        ) as cur:
            return (await cur.fetchone())["t"]

    async def get_brief(self, user_id: int) -> dict[str, Any]:
        async with self._db.execute("SELECT data FROM bot_briefs WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        return json.loads(row["data"]) if row else {}

    async def save_brief(self, user_id: int, data: dict[str, Any]) -> None:
        await self._db.execute(
            """INSERT INTO bot_briefs (user_id, data, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at""",
            (user_id, json.dumps(data, ensure_ascii=False), int(time.time())),
        )
        await self._db.commit()

    async def claim_lead(self, user_id: int) -> bool:
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT data FROM bot_briefs WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
            data = json.loads(row["data"]) if row else {}
            if data.get("_lead_sent"):
                await self._db.execute("COMMIT")
                return False
            data["_lead_sent"] = True
            data.pop("_awaiting_confirm", None)
            await self._db.execute(
                """INSERT INTO bot_briefs (user_id, data, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at""",
                (user_id, json.dumps(data, ensure_ascii=False), int(time.time())),
            )
            await self._db.execute("COMMIT")
            return True
        except Exception:
            await self._db.execute("ROLLBACK")
            raise

    async def reset_lead_flags(self, user_id: int) -> None:
        brief = await self.get_brief(user_id)
        if not brief:
            return
        brief.pop("_lead_sent", None)
        brief.pop("_awaiting_confirm", None)
        brief.pop("_followup_count", None)
        brief.pop("_last_followup_at", None)
        await self.save_brief(user_id, brief)

    async def create_lead(self, user_id: int, payload: str | None, summary: str) -> int:
        cur = await self._db.execute(
            "INSERT INTO bot_leads (user_id, payload, summary, created_at) VALUES (?, ?, ?, ?)",
            (user_id, payload, summary, int(time.time())),
        )
        await self._db.commit()
        return cur.lastrowid

    async def set_lead_status(self, lead_id: int, status: str, taken_by: int | None = None) -> None:
        await self._db.execute("UPDATE bot_leads SET status=?, taken_by=? WHERE id=?",
                               (status, taken_by, lead_id))
        await self._db.commit()

    async def recent_leads(self, limit: int = 10) -> list[dict[str, Any]]:
        async with self._db.execute(
            "SELECT * FROM bot_leads ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def log_event(self, kind: str, user_id: int | None = None, meta: str | None = None) -> None:
        await self._db.execute(
            "INSERT INTO bot_events (user_id, kind, meta, created_at) VALUES (?, ?, ?, ?)",
            (user_id, kind, meta, int(time.time())),
        )
        await self._db.commit()

    async def stats(self, days: int = 7) -> dict[str, Any]:
        since = int(time.time()) - days * 86400
        out: dict[str, Any] = {}
        async with self._db.execute(
            "SELECT kind, COUNT(*) c FROM bot_events WHERE created_at>=? GROUP BY kind", (since,)
        ) as cur:
            out["events"] = {r["kind"]: r["c"] for r in await cur.fetchall()}
        async with self._db.execute(
            "SELECT COALESCE(meta,'?') p, COUNT(*) c FROM bot_events "
            "WHERE kind='start' AND created_at>=? GROUP BY meta", (since,)
        ) as cur:
            out["starts_by_payload"] = {r["p"]: r["c"] for r in await cur.fetchall()}
        async with self._db.execute(
            "SELECT COUNT(*) c FROM bot_leads WHERE created_at>=?", (since,)
        ) as cur:
            out["leads"] = (await cur.fetchone())["c"]
        return out

    async def forget_user(self, user_id: int) -> None:
        for table in ("bot_messages", "bot_briefs", "bot_leads", "bot_events", "bot_users"):
            await self._db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        await self._db.commit()

    async def list_followup_candidates(self, silent_after_sec: int, max_followups: int = 2) -> list[dict]:
        cutoff = int(time.time()) - silent_after_sec
        async with self._db.execute(
            """
            SELECT u.user_id, u.lang, u.name, b.data AS brief_data, m.role AS last_role, m.created_at AS last_at
            FROM bot_users u
            JOIN (
                SELECT user_id, role, created_at FROM bot_messages
                WHERE id IN (SELECT MAX(id) FROM bot_messages GROUP BY user_id)
            ) m ON m.user_id = u.user_id
            LEFT JOIN bot_briefs b ON b.user_id = u.user_id
            WHERE u.reg_state = 'done' AND u.muted = 0
              AND m.role = 'assistant' AND m.created_at <= ?
            """,
            (cutoff,),
        ) as cur:
            rows = await cur.fetchall()
        out = []
        for r in rows:
            brief = json.loads(r["brief_data"]) if r["brief_data"] else {}
            if brief.get("_lead_sent"):
                continue
            count = int(brief.get("_followup_count") or 0)
            if count >= max_followups:
                continue
            last_fu = int(brief.get("_last_followup_at") or 0)
            if count >= 1 and int(time.time()) - last_fu < 86400:
                continue
            out.append({
                "user_id": r["user_id"],
                "lang": r["lang"] or "ru",
                "name": r["name"],
                "brief": brief,
                "awaiting_confirm": bool(brief.get("_awaiting_confirm")),
                "followup_count": count,
            })
        return out

    async def mark_followup_sent(self, user_id: int) -> None:
        brief = await self.get_brief(user_id)
        brief["_followup_count"] = int(brief.get("_followup_count") or 0) + 1
        brief["_last_followup_at"] = int(time.time())
        await self.save_brief(user_id, brief)

    async def purge_old_history(self) -> int:
        cutoff = int(time.time()) - RETENTION_DAYS * 86400
        cur = await self._db.execute("DELETE FROM bot_messages WHERE created_at<?", (cutoff,))
        await self._db.commit()
        return cur.rowcount


# Совместимость: прежнее имя класса
Storage = SqliteStorage
