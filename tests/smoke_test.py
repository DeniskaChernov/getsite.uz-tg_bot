"""Smoke-тест без сети: импорты, payload'ы, фильтры, шаблоны, хранилище."""
import asyncio
import os
import sys

os.environ.setdefault("BOT_TOKEN", "123456789:TEST_TOKEN_PLACEHOLDER_AAAAAAAAAAAAAAA")
os.environ.setdefault("ADMIN_CHAT_ID", "-100123")
os.environ.setdefault("ADMIN_IDS", "1,2")
os.environ.setdefault("DB_PATH", "data/test.db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.brief_flow import format_brief_summary, is_confirmation, is_edit_request
from app.filters import output_violation, polish_reply
from app.llm import brief_is_complete
from app.prompt import build_system_prompt, infer_dialog_stage
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
    # бот-продавец не «передаёт вопросы» и не упоминает график работы
    assert output_violation("Передал ваш вопрос Денису") == "handoff_phrase"
    assert output_violation("Передам заявку менеджеру") == "handoff_phrase"
    assert output_violation("Он ответит в рабочий день") == "handoff_phrase"
    assert output_violation("He will reply on a business day") == "handoff_phrase"
    assert output_violation("Сделаем лендинг за 10 рабочих дней") is None
    assert output_violation("Передам все пожелания в макет") is None


def test_confirmation_flow():
    assert is_confirmation("да")
    assert is_confirmation("Подтверждаю")
    assert is_confirmation("yes")
    assert is_confirmation("ha")
    assert not is_confirmation("да, но бюджет другой")
    assert is_edit_request("нужно поправить срок")
    assert is_edit_request("это неверно")
    brief = {
        "service": "лендинг",
        "niche": "кафе",
        "deadline": "к марту",
        "summary": "Нужен лендинг для кафе.",
    }
    summary = format_brief_summary(brief, "ru")
    assert "Подтверждаете все данные?" in summary
    assert "Услуга: лендинг" in summary
    assert "—" not in summary


def test_no_handoff_in_templates():
    from app.filters import output_violation as ov
    for d in (texts.LLM_FALLBACK_REPLY, texts.LEAD_CONFIRM_USER, texts.CONTACT_REPLY,
              texts.FORGET_CONFIRM_USER, texts.START_NO_PAYLOAD,
              texts.BRIEF_SUMMARY_HEADER, texts.BRIEF_SUMMARY_ASK, texts.BRIEF_EDIT_REPLY):
        for lang, s in d.items():
            assert ov(s) is None, f"handoff phrase in template [{lang}]: {s[:60]}"
    assert "Подтверждаете все данные?" in texts.BRIEF_SUMMARY_ASK["ru"]


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
              texts.FORGET_CONFIRM_USER, texts.RATE_LIMIT_REPLY,
              texts.ASK_NAME, texts.ASK_PHONE, texts.REG_DONE_PREFIX,
              texts.WELCOME_BACK, texts.NAME_TOO_LONG,
              texts.BRIEF_SUMMARY_HEADER, texts.BRIEF_SUMMARY_ASK,
              texts.BRIEF_EDIT_REPLY, texts.CONFIRM_YES_BTN, texts.CONFIRM_EDIT_BTN):
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
    p = build_system_prompt("Лендинг", "ru", "ниша: кафе", "Алишер", "уточнение задачи")
    assert "Лендинг" in p and "ниша: кафе" in p and "Алишер" in p
    assert "уточнение задачи" in p
    assert "ПОНИМАНИЕ КЛИЕНТА" in p
    assert 'на "вы"' in p
    assert "{" not in p  # все плейсхолдеры подставлены


def test_dialog_stage():
    assert "знакомство" in infer_dialog_stage({}, 1)
    assert "уточнение" in infer_dialog_stage({"service": "лендинг"}, 3)
    assert "подтверждения" in infer_dialog_stage({"service": "x"}, 5, awaiting_confirm=True)


def test_brief_state():
    full = {"service": "лендинг", "niche": "кафе",
            "summary": "Нужен лендинг для кафе.", "deadline": "к марту"}
    assert not brief_is_complete({}, 10)
    assert not brief_is_complete({"service": "лендинг"}, 10)
    assert brief_is_complete(full, 4)
    # мало сообщений клиента - лид не уходит, даже если поля заполнены
    assert not brief_is_complete(full, 2)
    assert not brief_is_complete(full, 0)


async def test_storage():
    if os.path.exists("data/test.db"):
        os.remove("data/test.db")
    s = Storage("data/test.db")
    await s.connect()
    await s.upsert_user(42, "testuser", "Test", "ru", "sites_landing")
    user = await s.get_user(42)
    assert user["payload"] == "sites_landing"
    # регистрация: язык → имя → телефон
    assert user["reg_state"] == "need_lang"
    await s.set_reg_state(42, "need_name")
    await s.set_name(42, "Алишер")
    await s.set_phone(42, "+998901234567")
    await s.set_reg_state(42, "done")
    user = await s.get_user(42)
    assert user["name"] == "Алишер" and user["phone"] == "+998901234567" and user["reg_state"] == "done"
    await s.add_message(42, "user", "привет")
    await s.add_message(42, "assistant", "здравствуйте")
    assert len(await s.history(42)) == 2
    await s.save_brief(42, {"niche": "кафе"})
    assert (await s.get_brief(42))["niche"] == "кафе"
    lead_id = await s.create_lead(42, "sites_landing", "Тестовый лид")
    await s.set_lead_status(lead_id, "taken", 1)
    leads = await s.recent_leads()
    assert leads[0]["status"] == "taken"
    # claim_lead: первый раз True, второй False
    await s.save_brief(42, {"service": "лендинг", "niche": "кафе", "summary": "тест", "deadline": "март"})
    assert await s.claim_lead(42) is True
    assert (await s.get_brief(42)).get("_lead_sent") is True
    assert await s.claim_lead(42) is False
    await s.reset_lead_flags(42)
    assert not (await s.get_brief(42)).get("_lead_sent")
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
    test_confirmation_flow()
    test_no_handoff_in_templates()
    test_polish()
    test_no_em_dash_in_templates()
    test_texts()
    test_prompt()
    test_dialog_stage()
    test_brief_state()
    asyncio.run(test_storage())
    # Импорт хендлеров и main — проверка, что всё собирается
    import app.handlers, app.admin, app.leads, main as entry  # noqa
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
