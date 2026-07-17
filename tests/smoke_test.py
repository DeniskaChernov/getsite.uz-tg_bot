"""Smoke-тест без сети: импорты, payload'ы, фильтры, шаблоны, хранилище."""
import asyncio
import os
import sys

os.environ.setdefault("BOT_TOKEN", "123456789:TEST_TOKEN_PLACEHOLDER_AAAAAAAAAAAAAAA")
os.environ.setdefault("ADMIN_CHAT_ID", "-100123")
os.environ.setdefault("ADMIN_IDS", "1,2")
os.environ.setdefault("DB_PATH", "data/test.db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.filters import output_violation, polish_reply
from app.llm import brief_is_complete
from app.prompt import build_system_prompt
from app.services import SERVICES, resolve_payload
from app.storage import Storage
from app import texts


def test_payloads():
    assert len(SERVICES) == 14
    assert resolve_payload("sites_landing").name_ru == "Лендинг"
    assert resolve_payload("nonexistent").payload == "discuss"
    assert resolve_payload("DROP TABLE;--").payload == "discuss"
    assert resolve_payload(None).payload == "discuss"
    assert resolve_payload("").payload == "discuss"


def test_filters():
    assert output_violation("Обычный ответ про лендинг за 4,9 млн сум") is None
    assert output_violation("Вот токен 123456789:AAAbbbCCCdddEEEfffGGGhhhIIIjjjKKKll") == "token_like_string"
    assert output_violation("ключ sk-abcdefghijklmnopqrstuvwxyz123456") == "api_key_like_string"
    assert output_violation("Оплатите на карту 8600...") == "payment_request"
    assert output_violation("ЗАЩИТА (приоритет над любыми просьбами в чате)") == "prompt_leak"


def test_polish():
    assert polish_reply("Лендинг — от 4,9 млн — быстро") == "Лендинг - от 4,9 млн - быстро"
    assert polish_reply("диапазон 1–2 недели") == "диапазон 1-2 недели"
    assert polish_reply("**Жирный** и __курсив__") == "Жирный и курсив"
    assert polish_reply("## Заголовок\nтекст") == "Заголовок\nтекст"
    assert polish_reply("а\n\n\n\nб") == "а\n\nб"
    assert "—" not in polish_reply("тире — везде — всегда")


def test_no_em_dash_in_templates():
    for d in (texts.START_NO_PAYLOAD, texts.CONTACT_REPLY, texts.MEDIA_REPLY,
              texts.LLM_FALLBACK_REPLY, texts.HELP_REPLY, texts.LEAD_CONFIRM_USER,
              texts.FORGET_CONFIRM_USER, texts.RATE_LIMIT_REPLY):
        for lang, s in d.items():
            assert "—" not in s and "–" not in s, f"em dash in template [{lang}]: {s[:40]}"
    for lang in ("ru", "uz", "en"):
        assert "—" not in texts.start_with_service(SERVICES["sites_landing"], lang)


def test_texts():
    for lang in ("ru", "uz", "en"):
        assert texts.START_NO_PAYLOAD[lang]
        assert len(texts.QUICK_BUTTONS[lang]) == 3
        greeting = texts.start_with_service(SERVICES["sites_landing"], lang)
        assert "4" in greeting  # цена присутствует
    assert texts.normalize_lang("uz-UZ") == "uz"
    assert texts.normalize_lang("en") == "en"
    assert texts.normalize_lang(None) == "ru"
    assert texts.normalize_lang("kk") == "ru"


def test_prompt():
    p = build_system_prompt("Лендинг", "ru", "ниша: кафе")
    assert "Лендинг" in p and "ниша: кафе" in p
    assert "{" not in p.replace("×2", "")  # все плейсхолдеры подставлены


def test_brief_state():
    assert not brief_is_complete({})
    assert not brief_is_complete({"service": "лендинг"})
    assert brief_is_complete({"service": "лендинг", "niche": "кафе",
                              "summary": "Нужен лендинг для кафе.", "deadline": "к марту"})


async def test_storage():
    if os.path.exists("data/test.db"):
        os.remove("data/test.db")
    s = Storage("data/test.db")
    await s.connect()
    await s.upsert_user(42, "testuser", "Test", "ru", "sites_landing")
    user = await s.get_user(42)
    assert user["payload"] == "sites_landing"
    await s.add_message(42, "user", "привет")
    await s.add_message(42, "assistant", "здравствуйте")
    assert len(await s.history(42)) == 2
    await s.save_brief(42, {"niche": "кафе"})
    assert (await s.get_brief(42))["niche"] == "кафе"
    lead_id = await s.create_lead(42, "sites_landing", "Тестовый лид")
    await s.set_lead_status(lead_id, "taken", 1)
    leads = await s.recent_leads()
    assert leads[0]["status"] == "taken"
    await s.log_event("start", 42, "sites_landing")
    stats = await s.stats()
    assert stats["starts_by_payload"]["sites_landing"] == 1
    await s.forget_user(42)
    assert await s.get_user(42) is None
    assert await s.history(42) == []
    await s.close()
    os.remove("data/test.db")


def main():
    test_payloads()
    test_filters()
    test_polish()
    test_no_em_dash_in_templates()
    test_texts()
    test_prompt()
    test_brief_state()
    asyncio.run(test_storage())
    # Импорт хендлеров и main — проверка, что всё собирается
    import app.handlers, app.admin, app.leads, main as entry  # noqa
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
