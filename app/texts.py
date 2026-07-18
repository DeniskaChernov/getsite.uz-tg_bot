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
    "ru": [("Рассчитать под мою задачу", "qb_estimate"), ("Сроки", "qb_timeline"), ("Связаться с менеджером", "qb_contact")],
    "uz": [("Vazifamga mos hisoblash", "qb_estimate"), ("Muddatlar", "qb_timeline"), ("Menejer bilan bog'lanish", "qb_contact")],
    "en": [("Estimate my project", "qb_estimate"), ("Timeline", "qb_timeline"), ("Contact a manager", "qb_contact")],
}

QUICK_BUTTON_AS_USER_TEXT = {
    "qb_estimate": {"ru": "Рассчитайте под мою задачу", "uz": "Vazifamga mos hisoblab bering", "en": "Please estimate my project"},
    "qb_timeline": {"ru": "Какие сроки?", "uz": "Muddatlar qanday?", "en": "What's the timeline?"},
}

CONTACT_REPLY = {
    "ru": f"Менеджер на связи: {CONTACT_TG}, {CONTACT_PHONE}. А пока расскажите, что за задача - помогу прикинуть объём и цену прямо здесь.",
    "uz": f"Menejer bilan bog'lanish: {CONTACT_TG}, {CONTACT_PHONE}. Ungacha vazifangizni aytib bering - hajm va narxni shu yerda chamalab beraman.",
    "en": f"You can reach a manager directly: {CONTACT_TG}, {CONTACT_PHONE}. Meanwhile, tell me about your task - I'll help estimate the scope and price right here.",
}

MEDIA_REPLY = {
    "ru": "Принял. Если есть ссылка на сайт или пример - пришлите текстом, сохраню в заявку. "
          "Файлы подробнее удобнее показать уже менеджеру.",
    "uz": "Qabul qildim. Sayt yoki namuna havolasi bo'lsa - matn bilan yuboring, arizaga yozib qo'yaman. "
          "Fayllarni batafsil menejerga ko'rsatish qulayroq.",
    "en": "Got it. If you have a link to a site or example - send it as text and I'll save it to the request. "
          "Files are easier to show a manager in detail later.",
}

LINK_SAVED_REPLY = {
    "ru": "Ссылку сохранил в заявку. Расскажите ещё коротко, что в ней важно для вас?",
    "uz": "Havolani arizaga yozib oldim. Unda siz uchun nima muhimligini qisqacha aytib bering?",
    "en": "I've saved the link to your request. Briefly - what about it matters most to you?",
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
    "ru": "Помогу выбрать услугу getsite, отвечу про цены и соберу короткий бриф для менеджера.\n\n"
          "/start - начать заново\n/lang ru|uz|en - сменить язык\n\n"
          f"Контакты: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
    "uz": "getsite xizmatini tanlashga yordam beraman, narxlar haqida javob beraman va menejer uchun qisqa brif tayyorlayman.\n\n"
          "/start - qaytadan boshlash\n/lang ru|uz|en - tilni o'zgartirish\n\n"
          f"Kontaktlar: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
    "en": "I'll help you choose a getsite service, answer pricing questions, and prepare a short brief for a manager.\n\n"
          "/start - start over\n/lang ru|uz|en - switch language\n\n"
          f"Contacts: {CONTACT_TG}, {CONTACT_PHONE}, https://getsite.uz",
}

LANG_CHANGED = {
    "ru": "Хорошо, продолжаем на русском.",
    "uz": "Yaxshi, o'zbek tilida davom etamiz.",
    "en": "OK, switching to English.",
}

FORGET_CONFIRM_USER = {
    "ru": "Готово. Ваши данные удалены из бота. Если снова напишете /start - начнём с чистого листа.",
    "uz": "Tayyor. Ma'lumotlaringiz botdan o'chirildi. Yana /start yozsangiz - yangidan boshlaymiz.",
    "en": "Done. Your data has been removed from the bot. If you send /start again - we'll start fresh.",
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
    "ru": f"Спасибо, данные принял. Передал менеджеру - он свяжется с вами в ближайшее время по смете и плану работ. "
          f"Если удобнее сразу: {CONTACT_PHONE}. Я на связи, если появятся вопросы.",
    "uz": f"Rahmat, ma'lumotlarni qabul qildim. Menejerga uzatdim - u smeta va ish rejasi bo'yicha tez orada siz bilan bog'lanadi. "
          f"Darhol qulayroq bo'lsa: {CONTACT_PHONE}. Savollar bo'lsa, men shu yerdaman.",
    "en": f"Thank you, I've recorded the details. I've passed this to a manager - they'll contact you shortly about the quote and work plan. "
          f"If it's easier to reach them now: {CONTACT_PHONE}. I'm here if you have more questions.",
}

BRIEF_EDIT_REPLY = {
    "ru": "Хорошо. Напишите, что поправить - и сверим ещё раз.",
    "uz": "Yaxshi. Nima tuzatish kerakligini yozing - keyin yana tekshirib chiqamiz.",
    "en": "Of course. Tell me what to correct - and we'll review again.",
}

# Мягкие напоминания, если клиент замолчал
FOLLOWUP_FIRST = {
    "ru": "Здравствуйте{name_part}! Если удобно продолжить - напишите, чем могу помочь по задаче. Я на связи.",
    "uz": "Assalomu alaykum{name_part}! Davom ettirish qulay bo'lsa - vazifa bo'yicha yozing. Men shu yerdaman.",
    "en": "Hello{name_part}! If you'd like to continue, just write about your task. I'm here.",
}

FOLLOWUP_SECOND = {
    "ru": "На всякий случай ещё раз: если проект актуален - напишите, сориентирую по шагам. Если нет - ничего страшного.",
    "uz": "Yana bir bor eslataman: loyiha dolzarb bo'lsa - yozing, qadamlarni aytib beraman. Bo'lmasa - hech qisi yo'q.",
    "en": "Just checking in: if the project is still relevant, write and I'll outline the next steps. If not - no worries.",
}

FOLLOWUP_THIRD = {
    "ru": "Последнее короткое сообщение от меня: если задача ещё в силе - я на связи и помогу сориентироваться. Если планы изменились - всё в порядке.",
    "uz": "Oxirgi qisqa xabarim: vazifa hali dolzarb bo'lsa - men shu yerdaman va yo'nalish beraman. Rejalar o'zgargan bo'lsa - hammasi joyida.",
    "en": "One last short note from me: if the task is still on - I'm here to help you get oriented. If plans changed - that's perfectly fine.",
}

FOLLOWUP_CONFIRM = {
    "ru": "Напомню: выше сводка по вашим данным. Если всё верно - подтвердите, пожалуйста. Если нужно поправить - напишите что именно.",
    "uz": "Eslatma: yuqorida ma'lumotlaringiz xulosasi bor. Hammasi to'g'ri bo'lsa - tasdiqlang. Tuzatish kerak bo'lsa - nima ekanini yozing.",
    "en": "A reminder: the summary of your details is above. If everything looks right - please confirm. If something needs fixing - tell me what.",
}
