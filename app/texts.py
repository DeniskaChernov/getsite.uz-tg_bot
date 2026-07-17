"""Шаблонные тексты (без LLM): регистрация, приветствия, fallback'и. RU / UZ / EN.

Стиль: живая переписка, обращение только на «вы», только обычные дефисы "-".
"""
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


# --- Регистрация: выбор языка сразу после /start ---

CHOOSE_LANG = (
    "Выберите язык / Tilni tanlang / Choose your language"
)

LANG_BUTTONS = [
    ("Русский", "lang_ru"),
    ("O'zbekcha", "lang_uz"),
    ("English", "lang_en"),
]

ASK_NAME = {
    "ru": "Отлично. Как я могу к вам обращаться?",
    "uz": "Ajoyib. Sizga qanday murojaat qilsam bo'ladi?",
    "en": "Great. How may I address you?",
}

ASK_PHONE = {
    "ru": "Приятно познакомиться, {name}! Оставите номер телефона? Так Денису будет проще с вами связаться. "
          "Нажмите кнопку ниже или отправьте номер текстом. Можно и пропустить.",
    "uz": "Tanishganimdan xursandman, {name}! Telefon raqamingizni qoldirasizmi? Shunda Denis siz bilan "
          "bog'lanishi osonroq bo'ladi. Quyidagi tugmani bosing yoki raqamni yozib yuboring. O'tkazib yuborsangiz ham bo'ladi.",
    "en": "Nice to meet you, {name}! Would you like to leave your phone number? It will make it easier for Denis "
          "to reach you. Tap the button below or type the number. You can also skip this step.",
}

SHARE_PHONE_BTN = {
    "ru": "Поделиться номером",
    "uz": "Raqamni yuborish",
    "en": "Share my number",
}

SKIP_BTN = {
    "ru": "Пропустить",
    "uz": "O'tkazib yuborish",
    "en": "Skip",
}

REG_DONE_PREFIX = {
    "ru": "Спасибо, записал!",
    "uz": "Rahmat, yozib oldim!",
    "en": "Thank you, noted!",
}

WELCOME_BACK = {
    "ru": "С возвращением, {name}!",
    "uz": "Qaytganingiz bilan, {name}!",
    "en": "Welcome back, {name}!",
}

NAME_TOO_LONG = {
    "ru": "Давайте покороче - просто имя, до 50 символов.",
    "uz": "Qisqaroq yozing, iltimos - faqat ism, 50 belgigacha.",
    "en": "A bit shorter, please - just a name, up to 50 characters.",
}

# --- Приветствия ---

START_NO_PAYLOAD = {
    "ru": "Я помощник getsite - помогу разобраться с задачей и прикинуть цену. "
          "Что вам нужно: сайт, Telegram-бот, автоматизация или поддержка?",
    "uz": "Men getsite yordamchisiman - vazifangizni aniqlab, narxni chamalab beraman. "
          "Sizga nima kerak: sayt, Telegram-bot, avtomatlashtirish yoki texnik yordam?",
    "en": "I'm the getsite assistant - I'll help clarify your task and estimate the price. "
          "What do you need: a website, a Telegram bot, automation, or support?",
}

_SERVICE_HOOK = {
    "ru": "Расскажите в двух словах, что у вас за бизнес - прикину точнее.",
    "uz": "Biznesingiz haqida qisqacha aytib bering - aniqroq chamalab beraman.",
    "en": "Tell me a bit about your business and I'll give you a closer estimate.",
}


def start_with_service(svc: Service, lang: Lang) -> str:
    name = {"ru": svc.name_ru, "uz": svc.name_uz, "en": svc.name_en}[lang]
    price = {"ru": svc.price_ru, "uz": svc.price_uz, "en": svc.price_en}[lang]
    if lang == "uz":
        head = f"Ko'rib turibman, sizni {name} qiziqtiradi."
        price_line = f" Odatda {price}, aniq summa - qisqa brifdan keyin." if price else ""
    elif lang == "en":
        head = f"I see you're interested in a {name.lower()}."
        price_line = f" It usually starts {price}, the exact quote comes after a short brief." if price else ""
    else:
        head = f"Вижу, вас интересует {name.lower() if name != 'CRM с нуля' else name}."
        price_line = f" Обычно {price}, точная сумма - после короткого брифа." if price else ""
    return f"{head}{price_line} {_SERVICE_HOOK[lang]}"


QUICK_BUTTONS = {
    "ru": [("Рассчитать под мою задачу", "qb_estimate"), ("Сроки", "qb_timeline"), ("Связаться с Денисом", "qb_contact")],
    "uz": [("Vazifamga mos hisoblash", "qb_estimate"), ("Muddatlar", "qb_timeline"), ("Denis bilan bog'lanish", "qb_contact")],
    "en": [("Estimate my project", "qb_estimate"), ("Timeline", "qb_timeline"), ("Contact Denis", "qb_contact")],
}

QUICK_BUTTON_AS_USER_TEXT = {
    "qb_estimate": {"ru": "Рассчитайте под мою задачу", "uz": "Vazifamga mos hisoblab bering", "en": "Please estimate my project"},
    "qb_timeline": {"ru": "Какие сроки?", "uz": "Muddatlar qanday?", "en": "What's the timeline?"},
}

CONTACT_REPLY = {
    "ru": f"Денис на связи: {CONTACT_TG}, {CONTACT_PHONE}. Если коротко опишете задачу здесь - передам сразу с контекстом.",
    "uz": f"Denis bilan bog'lanish: {CONTACT_TG}, {CONTACT_PHONE}. Vazifangizni shu yerda qisqacha yozsangiz - kontekst bilan darhol uzataman.",
    "en": f"You can reach Denis directly: {CONTACT_TG}, {CONTACT_PHONE}. Describe your task briefly here and I'll pass it along with context.",
}

MEDIA_REPLY = {
    "ru": "Давайте пока текстом - файлы и примеры вы сможете показать уже Денису.",
    "uz": "Hozircha matn bilan yozing - fayl va namunalarni keyin Denisga ko'rsatasiz.",
    "en": "Let's stick to text for now - you can share files and examples with Denis later.",
}

TOO_LONG_REPLY = {
    "ru": "Прочитал, отвечаю по сути.",
    "uz": "O'qib chiqdim, mohiyati bo'yicha javob beraman.",
    "en": "Got it, replying to the main point.",
}

RATE_LIMIT_REPLY = {
    "ru": "Секунду, отвечаю по одному сообщению.",
    "uz": "Bir soniya, xabarlarga birma-bir javob beraman.",
    "en": "One second, I reply one message at a time.",
}

LLM_WAIT_REPLY = {
    "ru": "Секунду, уточняю...",
    "uz": "Bir soniya, aniqlashtiryapman...",
    "en": "One second, checking...",
}

LLM_FALLBACK_REPLY = {
    "ru": f"Передал ваш вопрос Денису - он ответит в рабочий день. Если срочно: {CONTACT_TG}, {CONTACT_PHONE}.",
    "uz": f"Savolingizni Denisga uzatdim - ish kunida javob beradi. Shoshilinch bo'lsa: {CONTACT_TG}, {CONTACT_PHONE}.",
    "en": f"I've passed your question to Denis - he'll reply on a business day. If urgent: {CONTACT_TG}, {CONTACT_PHONE}.",
}

FILTERED_REPLY = LLM_FALLBACK_REPLY

HELP_REPLY = {
    "ru": "Помогу выбрать услугу getsite, отвечу про цены и соберу короткий бриф для Дениса.\n\n"
          "/start - начать заново\n/lang ru|uz|en - сменить язык\n\n"
          f"Контакты: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
    "uz": "getsite xizmatini tanlashga yordam beraman, narxlar haqida javob beraman va Denis uchun qisqa brif tayyorlayman.\n\n"
          "/start - qaytadan boshlash\n/lang ru|uz|en - tilni o'zgartirish\n\n"
          f"Kontaktlar: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
    "en": "I'll help you choose a getsite service, answer pricing questions, and prepare a short brief for Denis.\n\n"
          "/start - start over\n/lang ru|uz|en - switch language\n\n"
          f"Contacts: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
}

LANG_CHANGED = {
    "ru": "Хорошо, продолжаем на русском.",
    "uz": "Yaxshi, o'zbek tilida davom etamiz.",
    "en": "OK, switching to English.",
}

FORGET_CONFIRM_USER = {
    "ru": "Принял. Передал запрос на удаление ваших данных - администратор подтвердит удаление.",
    "uz": "Qabul qildim. Ma'lumotlaringizni o'chirish so'rovini uzatdim - administrator o'chirishni tasdiqlaydi.",
    "en": "Understood. I've forwarded your data deletion request - an administrator will confirm the removal.",
}

LEAD_CONFIRM_USER = {
    "ru": f"Всё зафиксировал. Передаю Денису - он ответит вам в рабочий день. Если срочно: {CONTACT_PHONE}.",
    "uz": f"Hammasini qayd etdim. Denisga uzatyapman - ish kunida sizga javob beradi. Shoshilinch bo'lsa: {CONTACT_PHONE}.",
    "en": f"All noted. I'm passing this to Denis - he'll get back to you on a business day. If urgent: {CONTACT_PHONE}.",
}
