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


# --- Регистрация: выбор языка сразу после /start, в фирменном тоне getsite ---

CHOOSE_LANG = (
    "Здравствуйте! Salom! Hello! 👋\n\n"
    "Вы обратились в getsite - мы разрабатываем сайты, Telegram-ботов и автоматизацию для бизнеса.\n\n"
    "Выберите, пожалуйста, удобный язык общения:"
)

LANG_BUTTONS = [
    ("🇷🇺 Русский", "lang_ru"),
    ("🇺🇿 O'zbekcha", "lang_uz"),
    ("🇬🇧 English", "lang_en"),
]

ASK_NAME = {
    "ru": "Рад приветствовать! Подскажите, пожалуйста, как я могу к вам обращаться?",
    "uz": "Xush kelibsiz! Ayting-chi, sizga qanday murojaat qilsam bo'ladi?",
    "en": "Welcome! Could you tell me how I may address you?",
}

ASK_PHONE = {
    "ru": "{name}, приятно познакомиться! Если удобно, оставьте номер телефона - пригодится, "
          "когда дойдёт до обсуждения деталей проекта. Никаких рассылок, только по делу. "
          "Этот шаг можно пропустить.",
    "uz": "{name}, tanishganimdan xursandman! Qulay bo'lsa, telefon raqamingizni qoldiring - loyiha "
          "tafsilotlarini muhokama qilishda kerak bo'ladi. Hech qanday tarqatmalar, faqat ish yuzasidan. "
          "Bu qadamni o'tkazib yuborishingiz ham mumkin.",
    "en": "{name}, pleased to meet you! If convenient, leave your phone number - it will be useful "
          "when we get to discussing project details. No mailings, business only. "
          "You can also skip this step.",
}

SHARE_PHONE_BTN = {
    "ru": "📱 Поделиться номером",
    "uz": "📱 Raqamni yuborish",
    "en": "📱 Share my number",
}

SKIP_BTN = {
    "ru": "Пропустить",
    "uz": "O'tkazib yuborish",
    "en": "Skip",
}

REG_DONE_PREFIX = {
    "ru": "Спасибо, записал.",
    "uz": "Rahmat, yozib oldim.",
    "en": "Thank you, noted.",
}

WELCOME_BACK = {
    "ru": "С возвращением, {name}!",
    "uz": "Qaytganingiz bilan, {name}!",
    "en": "Welcome back, {name}!",
}

NAME_TOO_LONG = {
    "ru": "Подскажите, пожалуйста, просто имя - до 50 символов.",
    "uz": "Iltimos, faqat ismingizni yozing - 50 belgigacha.",
    "en": "Just a name, please - up to 50 characters.",
}

# --- Приветствия ---

START_NO_PAYLOAD = {
    "ru": "Расскажите, пожалуйста, какая задача перед вами стоит: сайт, Telegram-бот, "
          "автоматизация или поддержка? Помогу сориентироваться по объёму и стоимости.",
    "uz": "Ayting-chi, oldingizda qanday vazifa turibdi: sayt, Telegram-bot, avtomatlashtirish "
          "yoki texnik yordam? Hajm va narx bo'yicha yo'nalish beraman.",
    "en": "Please tell me what you're looking for: a website, a Telegram bot, automation, "
          "or support? I'll help you understand the scope and cost.",
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
    "ru": f"Денис на связи: {CONTACT_TG}, {CONTACT_PHONE}. А пока расскажите, что за задача - помогу прикинуть объём и цену прямо здесь.",
    "uz": f"Denis bilan bog'lanish: {CONTACT_TG}, {CONTACT_PHONE}. Ungacha vazifangizni aytib bering - hajm va narxni shu yerda chamalab beraman.",
    "en": f"You can reach Denis directly: {CONTACT_TG}, {CONTACT_PHONE}. Meanwhile, tell me about your task - I'll help estimate the scope and price right here.",
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
    "ru": "Кажется, связь прервалась - повторите, пожалуйста, сообщение. Я на связи.",
    "uz": "Aloqa uzilib qoldi shekilli - xabaringizni qayta yuboring, iltimos. Men shu yerdaman.",
    "en": "It seems the connection dropped - please send your message again. I'm here.",
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
    "ru": "Принял запрос на удаление ваших данных - удалим в ближайшее время.",
    "uz": "Ma'lumotlaringizni o'chirish so'rovini qabul qildim - tez orada o'chiramiz.",
    "en": "Your data deletion request has been received - we'll remove it shortly.",
}

# Сводка брифа перед отправкой лида - клиент должен явно подтвердить
BRIEF_SUMMARY_HEADER = {
    "ru": "Давайте сверим, всё ли верно:",
    "uz": "Keling, hammasi to'g'riligini tekshirib olaylik:",
    "en": "Let me confirm everything is correct:",
}

BRIEF_SUMMARY_ASK = {
    "ru": "Подтверждаете все данные?",
    "uz": "Barcha ma'lumotlarni tasdiqlaysizmi?",
    "en": "Do you confirm all these details?",
}

BRIEF_FIELD_LABELS = {
    "ru": {
        "service": "Услуга",
        "niche": "Ниша / бизнес",
        "deadline": "Срок",
        "budget_hint": "Бюджет",
        "contact": "Контакт",
        "links": "Ссылки",
        "summary": "Суть",
    },
    "uz": {
        "service": "Xizmat",
        "niche": "Soha / biznes",
        "deadline": "Muddat",
        "budget_hint": "Byudjet",
        "contact": "Kontakt",
        "links": "Havolalar",
        "summary": "Mohiyat",
    },
    "en": {
        "service": "Service",
        "niche": "Niche / business",
        "deadline": "Deadline",
        "budget_hint": "Budget",
        "contact": "Contact",
        "links": "Links",
        "summary": "Summary",
    },
}

CONFIRM_YES_BTN = {
    "ru": "Да, подтверждаю",
    "uz": "Ha, tasdiqlayman",
    "en": "Yes, I confirm",
}

CONFIRM_EDIT_BTN = {
    "ru": "Нужно поправить",
    "uz": "Tuzatish kerak",
    "en": "I need to correct something",
}

LEAD_CONFIRM_USER = {
    "ru": f"Спасибо, данные принял. Денис свяжется с вами в ближайшее время по смете и плану работ. "
          f"Если удобнее сразу: {CONTACT_PHONE}. Я на связи, если появятся вопросы.",
    "uz": f"Rahmat, ma'lumotlarni qabul qildim. Denis smeta va ish rejasi bo'yicha tez orada siz bilan bog'lanadi. "
          f"Darhol qulayroq bo'lsa: {CONTACT_PHONE}. Savollar bo'lsa, men shu yerdaman.",
    "en": f"Thank you, I've recorded the details. Denis will contact you shortly about the quote and work plan. "
          f"If it's easier to reach him now: {CONTACT_PHONE}. I'm here if you have more questions.",
}

BRIEF_EDIT_REPLY = {
    "ru": "Хорошо. Напишите, что поправить - и сверим ещё раз.",
    "uz": "Yaxshi. Nima tuzatish kerakligini yozing - keyin yana tekshirib chiqamiz.",
    "en": "Of course. Tell me what to correct - and we'll review again.",
}
