# getsite.uz — Telegram-бот продаж (@getsiteuzbot)

Первая линия продаж [getsite.uz](https://getsite.uz): встречает клиента по deep-link с сайта, ведёт живой диалог через LLM, собирает мини-бриф и передаёт лид в админ-группу. Полное ТЗ: `docs/telegram-bot-prompt.md` в репозитории сайта.

## Стек

- Python 3.12, aiogram 3, aiohttp (webhook-сервер)
- PostgreSQL (asyncpg) — общая БД с сайтом getsite.uz, в перспективе с CRM; таблицы с префиксом `bot_`
- SQLite (aiosqlite) — локальная разработка без `DATABASE_URL`
- Любой OpenAI-совместимый LLM API (OpenAI / OpenRouter / ...)

## Регистрация клиента

После /start: выбор языка (RU / UZ / EN) → имя («Как я могу к вам обращаться?») → телефон
(кнопка «Поделиться номером» или текстом, можно пропустить) → приветствие по услуге из deep-link.
Клиент запоминается: при повторном /start бот здоровается по имени и продолжает с сохранённым брифом.
Общение — только на «вы», обычные дефисы «-» гарантируются пост-обработкой ответов LLM.

## Структура

```
main.py            # точка входа: webhook или polling
app/config.py      # конфиг из переменных окружения
app/services.py    # каталог услуг и deep-link payload'ов
app/texts.py       # шаблонные тексты RU/UZ/EN (без LLM)
app/prompt.py      # системный промпт v2 + промпт извлечения брифа
app/llm.py         # LLM-слой: очередь, таймаут 30с, выходной фильтр
app/filters.py     # фильтры: токены, ключи, оплата, утечка промпта
app/ratelimit.py   # анти-флуд и глобальный circuit breaker
app/handlers.py    # пользовательские хендлеры и edge cases
app/admin.py       # /leads /stats /forget /mute + кнопки лидов
app/leads.py       # карточка лида в админ-группу
app/storage.py     # SQLite: схема + retention 90 дней
```

## Быстрый старт (локально, polling)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # заполнить BOT_TOKEN, ADMIN_CHAT_ID, ADMIN_IDS, LLM_API_KEY
# в .env поставить MODE=polling
python main.py
```

## Продакшен (webhook, Railway / VPS)

1. Задать секреты в переменных окружения платформы (не в git!): все из `.env.example`, `MODE=webhook`.
2. `WEBHOOK_SECRET` и `WEBHOOK_PATH_SECRET` — случайные: `openssl rand -hex 16`.
3. Деплой контейнера (`Dockerfile` в корне). Бот сам вызывает `setWebhook` при старте с `secret_token` и `allowed_updates=[message, callback_query, my_chat_member]`.
4. Health-check: `GET /health` — 200, если вебхук без ошибок; 503 при `last_error_date`.
5. Данные: примонтировать volume на `/app/data` (SQLite + ежедневный retention-purge истории старше 90 дней). Настроить бэкап volume.

## Безопасность (реализовано по ТЗ, раздел 4)

- Секреты только в env; в коде, логах и ответах бота их нет.
- Webhook: проверка `X-Telegram-Bot-Api-Secret-Token` (мусор отклоняется), неугадываемый путь `/tg/<random>`, тело ≤ 1 МБ, только POST.
- Rate-limit: 1 LLM-запрос / 3 сек, 30 сообщений / 10 минут на пользователя; глобальный circuit breaker с алертом в админ-группу.
- Вход: обрезка до 2000 символов; медиа/войсы в LLM не передаются; пересланные сообщения и другие боты игнорируются.
- LLM: сообщения клиента только как user-роль; выходной фильтр ловит токен-подобные строки, ключи API, «оплатите на карту» и фрагменты системного промпта.
- Отправка лида — только детерминированный код по извлечённому состоянию брифа; у модели нет инструментов.
- Приватность: минимум полей, история 90 дней, `/forget <user_id>` удаляет всё, логи без текста сообщений.
- Админ-команды — только для user_id из `ADMIN_IDS` (не по username).

## Настройка в BotFather (вручную, чеклист)

- `/setjoingroups` → Disable
- Inline mode → выключен
- Отдельный токен для staging-бота

## Deep-links с сайта

`https://t.me/getsiteuzbot?start=<payload>` — 14 payload'ов (см. `app/services.py`).
Невалидный payload → сценарий `discuss`. Payload логируется в лид как источник.

## Команды

Клиент: `/start`, `/help`, `/lang ru|uz|en`
Админ: `/leads`, `/stats`, `/forget <user_id>`, `/mute <user_id> [off]`

## Осталось заполнить владельцу (раздел 10 ТЗ)

1. Финальный токен и `chat_id` админ-группы → в секреты.
2. Куда дублировать лиды (Google Sheets / CRM) — сейчас только админ-группа + SQLite.
3. Рабочие часы и SLA ответа менеджера.
4. UZ-версии ключевых фраз — проверить носителем (черновики в `app/texts.py`).
5. Правила эскалации «клиент злой / срочно».
