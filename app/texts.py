"""Шаблонные тексты (без LLM): приветствия, fallback'и, сервисные ответы. RU / UZ / EN."""
from __future__ import annotations

from app.services import Service

CONTACT_PHONE = "+998 91 908-06-21"
CONTACT_TG = "@getsiteuz"

Lang = str  # "ru" | "uz" | "en"


def normalize_lang(code: str | None) -> Lang:
    if not code:
        return "ru"
    code = code.lower()
    if code.startswith("uz"):
        return "uz"
    if code.startswith("en"):
        return "en"
    return "ru"


START_NO_PAYLOAD = {
    "ru": "Привет! Я бот getsite — помогу понять задачу и собрать короткое ТЗ. "
          "Что нужно: сайт, Telegram-бот, автоматизация или поддержка?",
    "uz": "Salom! Men getsite botiman — vazifangizni tushunib, qisqa TZ yig'ishga yordam beraman. "
          "Nima kerak: sayt, Telegram-bot, avtomatlashtirish yoki qo'llab-quvvatlash?",
    "en": "Hi! I'm the getsite bot — I'll help clarify your task and put together a short brief. "
          "What do you need: a website, a Telegram bot, automation, or support?",
}

# Что влияет на цену — короткая фраза для приветствия по услуге
_SERVICE_HOOK = {
    "ru": "Чтобы прикинуть точнее: для какой ниши это нужно и есть ли уже примеры, которые нравятся?",
    "uz": "Aniqroq hisoblash uchun: bu qaysi soha uchun kerak va sizga yoqqan namunalar bormi?",
    "en": "To estimate more precisely: what niche is this for, and do you have examples you like?",
}


def start_with_service(svc: Service, lang: Lang) -> str:
    name = {"ru": svc.name_ru, "uz": svc.name_uz, "en": svc.name_en}[lang]
    price = {"ru": svc.price_ru, "uz": svc.price_uz, "en": svc.price_en}[lang]
    if lang == "uz":
        head = f"Salom! Ko'ryapman, sizni «{name}» qiziqtiryapti."
        price_line = f" Odatda narx {price} — aniq summa qisqa brifdan keyin." if price else ""
    elif lang == "en":
        head = f"Hi! I see you're interested in {name}."
        price_line = f" It usually starts {price} — the exact quote comes after a short brief." if price else ""
    else:
        head = f"Привет! Вижу, интересует {name.lower() if name != 'CRM с нуля' else name}."
        price_line = f" Обычно {price} — точная сумма после короткого брифа." if price else ""
    return f"{head}{price_line} {_SERVICE_HOOK[lang]}"


QUICK_BUTTONS = {
    "ru": [("Рассчитать под мою задачу", "qb_estimate"), ("Сроки", "qb_timeline"), ("Связаться с Денисом", "qb_contact")],
    "uz": [("Mening vazifamga hisoblash", "qb_estimate"), ("Muddatlar", "qb_timeline"), ("Denis bilan bog'lanish", "qb_contact")],
    "en": [("Estimate my project", "qb_estimate"), ("Timeline", "qb_timeline"), ("Contact Denis", "qb_contact")],
}

# Текст, который уходит в LLM как сообщение пользователя при нажатии кнопки
QUICK_BUTTON_AS_USER_TEXT = {
    "qb_estimate": {"ru": "Рассчитайте под мою задачу", "uz": "Mening vazifamga hisoblang", "en": "Estimate my project"},
    "qb_timeline": {"ru": "Какие сроки?", "uz": "Muddatlar qanday?", "en": "What's the timeline?"},
}

CONTACT_REPLY = {
    "ru": f"Денис на связи: {CONTACT_TG}, {CONTACT_PHONE}. Если коротко опишете задачу здесь — передам сразу с контекстом.",
    "uz": f"Denis bilan bog'lanish: {CONTACT_TG}, {CONTACT_PHONE}. Vazifani shu yerda qisqacha yozsangiz — kontekst bilan darhol uzataman.",
    "en": f"You can reach Denis: {CONTACT_TG}, {CONTACT_PHONE}. Describe your task briefly here and I'll pass it along with context.",
}

MEDIA_REPLY = {
    "ru": "Пришлите, пожалуйста, текстом — файлы и примеры покажете уже Денису.",
    "uz": "Iltimos, matn bilan yozing — fayl va namunalarni Denisga ko'rsatasiz.",
    "en": "Please send it as text — you can share files and examples with Denis later.",
}

TOO_LONG_REPLY = {
    "ru": "Прочитал, отвечаю по сути.",
    "uz": "O'qidim, mohiyati bo'yicha javob beraman.",
    "en": "Got it, replying to the main point.",
}

RATE_LIMIT_REPLY = {
    "ru": "Отвечаю по одному сообщению — секунду.",
    "uz": "Xabarlarga birma-bir javob beraman — bir soniya.",
    "en": "I reply one message at a time — just a second.",
}

LLM_WAIT_REPLY = {
    "ru": "Секунду, уточняю…",
    "uz": "Bir soniya, aniqlashtiryapman…",
    "en": "One second, checking…",
}

LLM_FALLBACK_REPLY = {
    "ru": f"Передал вопрос Денису — он ответит в рабочий день. Если срочно: {CONTACT_TG}, {CONTACT_PHONE}.",
    "uz": f"Savolni Denisga uzatdim — ish kunida javob beradi. Shoshilinch bo'lsa: {CONTACT_TG}, {CONTACT_PHONE}.",
    "en": f"I've passed your question to Denis — he'll reply on a business day. If urgent: {CONTACT_TG}, {CONTACT_PHONE}.",
}

FILTERED_REPLY = LLM_FALLBACK_REPLY  # ответ при срабатывании выходного фильтра

HELP_REPLY = {
    "ru": "Я помогу выбрать услугу getsite, отвечу на вопросы по ценам и соберу короткий бриф для Дениса.\n\n"
          "Команды:\n/start — начать заново\n/lang ru|uz|en — сменить язык\n\n"
          f"Контакты: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
    "uz": "Men getsite xizmatini tanlashga yordam beraman, narxlar bo'yicha savollarga javob beraman va Denis uchun qisqa brif yig'aman.\n\n"
          "Buyruqlar:\n/start — qaytadan boshlash\n/lang ru|uz|en — tilni o'zgartirish\n\n"
          f"Kontaktlar: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
    "en": "I'll help you pick a getsite service, answer pricing questions, and collect a short brief for Denis.\n\n"
          "Commands:\n/start — start over\n/lang ru|uz|en — switch language\n\n"
          f"Contacts: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
}

LANG_CHANGED = {
    "ru": "Ок, продолжаем на русском.",
    "uz": "Yaxshi, o'zbek tilida davom etamiz.",
    "en": "OK, switching to English.",
}

FORGET_CONFIRM_USER = {
    "ru": "Принял. Передал запрос на удаление ваших данных — админ подтвердит удаление.",
    "uz": "Qabul qildim. Ma'lumotlaringizni o'chirish so'rovini uzatdim — admin tasdiqlaydi.",
    "en": "Got it. I've forwarded your data deletion request — an admin will confirm the removal.",
}

LEAD_CONFIRM_USER = {
    "ru": f"Ок, зафиксировал. Передаю Денису — он ответит в рабочий день. Если срочно: {CONTACT_PHONE}.",
    "uz": f"Yaxshi, qayd etdim. Denisga uzatyapman — ish kunida javob beradi. Shoshilinch bo'lsa: {CONTACT_PHONE}.",
    "en": f"OK, noted. Passing this to Denis — he'll reply on a business day. If urgent: {CONTACT_PHONE}.",
}
