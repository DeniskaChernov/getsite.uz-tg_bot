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
    "Привет! Salom! Hello! 👋\n\n"
    "Я помощник getsite - мы делаем сайты и ботов, которые приносят заявки, "
    "а не просто красиво висят в интернете.\n\n"
    "Сначала о главном - на каком языке вам удобнее?"
)

LANG_BUTTONS = [
    ("🇷🇺 Русский", "lang_ru"),
    ("🇺🇿 O'zbekcha", "lang_uz"),
    ("🇬🇧 English", "lang_en"),
]

ASK_NAME = {
    "ru": "Отлично, договорились. Чтобы не обращаться к вам «уважаемый клиент» - как вас зовут?",
    "uz": "Kelishdik. Sizga «hurmatli mijoz» deb murojaat qilmaslik uchun - ismingiz nima?",
    "en": "Perfect. So I don't have to call you \"dear customer\" - what's your name?",
}

ASK_PHONE = {
    "ru": "{name}, рад знакомству! Оставите номер телефона? Обещаю: никакого спама и рассылок - "
          "он нужен только, чтобы обсудить ваш проект голосом, если дойдёт до дела. "
          "Не хотите - смело жмите «Пропустить».",
    "uz": "{name}, tanishganimdan xursandman! Telefon raqamingizni qoldirasizmi? Va'da beraman: hech qanday "
          "spam va tarqatmalar bo'lmaydi - u faqat loyihangizni ovozda muhokama qilish uchun kerak. "
          "Xohlamasangiz - bemalol «O'tkazib yuborish» tugmasini bosing.",
    "en": "{name}, great to meet you! Would you like to leave your phone number? I promise: no spam, "
          "no newsletters - it's only for discussing your project by voice if it comes to that. "
          "Not keen - just tap \"Skip\".",
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
    "ru": "Отлично, записал. Теперь к делу!",
    "uz": "Ajoyib, yozib oldim. Endi ishga o'tamiz!",
    "en": "Great, noted. Now, down to business!",
}

WELCOME_BACK = {
    "ru": "С возвращением, {name}! Рад вас видеть.",
    "uz": "Qaytganingiz bilan, {name}! Sizni ko'rganimdan xursandman.",
    "en": "Welcome back, {name}! Good to see you.",
}

NAME_TOO_LONG = {
    "ru": "Ого, длинновато для имени. Давайте покороче - до 50 символов.",
    "uz": "Ism uchun biroz uzun-ku. Qisqaroq yozing - 50 belgigacha.",
    "en": "That's a bit long for a name. Something shorter, please - up to 50 characters.",
}

# --- Приветствия ---

START_NO_PAYLOAD = {
    "ru": "Итак, чем займёмся? Сайт, Telegram-бот, автоматизация или поддержка - "
          "расскажите про задачу, помогу прикинуть объём и цену.",
    "uz": "Xo'sh, nimadan boshlaymiz? Sayt, Telegram-bot, avtomatlashtirish yoki texnik yordam - "
          "vazifangizni aytib bering, hajm va narxni chamalab beraman.",
    "en": "So, what are we building? A website, a Telegram bot, automation, or support - "
          "tell me about your task and I'll help estimate the scope and price.",
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
    "ru": "Хм, связь моргнула - повторите, пожалуйста, сообщение. Я на месте.",
    "uz": "Aloqa biroz uzildi - xabaringizni qayta yuboring, iltimos. Men shu yerdaman.",
    "en": "Hmm, the connection blinked - please send that again. I'm right here.",
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

LEAD_CONFIRM_USER = {
    "ru": f"Отлично, все детали у меня. Следующий шаг - смета и план работ: Денис свяжется с вами в ближайшее время. "
          f"Хотите быстрее - наберите его сами: {CONTACT_PHONE}. А я на связи, если появятся вопросы.",
    "uz": f"Ajoyib, barcha tafsilotlar menda. Keyingi qadam - smeta va ish rejasi: Denis tez orada siz bilan bog'lanadi. "
          f"Tezroq xohlasangiz - o'zingiz qo'ng'iroq qiling: {CONTACT_PHONE}. Savollar bo'lsa, men shu yerdaman.",
    "en": f"Great, I have all the details. Next step is the quote and work plan: Denis will contact you shortly. "
          f"Want it faster - call him directly: {CONTACT_PHONE}. And I'm here if you have more questions.",
}
