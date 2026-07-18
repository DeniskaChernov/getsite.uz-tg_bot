"""Точка входа: webhook (продакшен) или long polling (локальная разработка).

Логи — только метаданные, без текста сообщений и секретов.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app import admin, handlers
from app.config import config
from app.followups import followup_loop
from app.storage import BotStorage, create_storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("main")

ALLOWED_UPDATES = ["message", "callback_query", "my_chat_member"]
MAX_BODY_SIZE = 1024 * 1024  # 1 МБ


async def daily_maintenance(storage: BotStorage) -> None:
    while True:
        await asyncio.sleep(86400)
        try:
            removed = await storage.purge_old_history()
            log.info("Retention purge: %s old messages removed", removed)
        except Exception:
            log.error("Retention purge failed", exc_info=True)


async def health(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    storage: BotStorage = request.app["storage"]
    try:
        info = await bot.get_webhook_info()
        webhook_ok = not info.last_error_date
        db_ok = await storage.ping()
        ok = webhook_ok and db_ok
        return web.json_response(
            {
                "status": "ok" if ok else "degraded",
                "webhook_ok": webhook_ok,
                "db_ok": db_ok,
                "pending": info.pending_update_count,
            },
            status=200 if ok else 503,
        )
    except Exception:
        return web.json_response({"status": "error"}, status=503)


def build_dispatcher(storage: BotStorage) -> Dispatcher:
    # Ключ workflow_data "storage" внедряется в хендлеры по имени аргумента.
    # Нельзя передавать storage= в конструктор: этот параметр зарезервирован под FSM.
    dp = Dispatcher()
    dp["storage"] = storage
    dp.include_router(admin.router)
    dp.include_router(handlers.router)
    return dp


async def run_polling(bot: Bot, dp: Dispatcher, storage: BotStorage) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Starting in POLLING mode (dev only)")
    asyncio.create_task(daily_maintenance(storage))
    asyncio.create_task(followup_loop(bot, storage))
    await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)


async def run_webhook(bot: Bot, dp: Dispatcher, storage: BotStorage) -> None:
    assert config.webhook_base_url and config.webhook_secret and config.webhook_path_secret, \
        "WEBHOOK_BASE_URL, WEBHOOK_SECRET и WEBHOOK_PATH_SECRET обязательны в режиме webhook"

    app = web.Application(client_max_size=MAX_BODY_SIZE)
    app["bot"] = bot
    app["storage"] = storage
    # Проверка X-Telegram-Bot-Api-Secret-Token: несовпадение → 401/403 внутри handler'а
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=config.webhook_secret).register(
        app, path=config.webhook_path,
    )
    app.router.add_get("/health", health)
    setup_application(app, dp, bot=bot)

    await bot.set_webhook(
        url=config.webhook_url,
        secret_token=config.webhook_secret,
        allowed_updates=ALLOWED_UPDATES,
        drop_pending_updates=True,
    )
    log.info("Webhook set, starting server on port %s", config.port)

    asyncio.create_task(daily_maintenance(storage))
    asyncio.create_task(followup_loop(bot, storage))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=config.port)
    await site.start()
    await asyncio.Event().wait()


async def main() -> None:
    # Postgres (DATABASE_URL, общая БД с сайтом и будущей CRM) или SQLite локально
    storage = create_storage()
    await storage.connect()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties())
    dp = build_dispatcher(storage)

    try:
        if config.mode == "webhook":
            await run_webhook(bot, dp, storage)
        else:
            await run_polling(bot, dp, storage)
    finally:
        await storage.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Stopped")
