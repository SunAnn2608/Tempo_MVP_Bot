"""
🎵 Tempo Bot — Конфигурация
УТП: Помоги себе избежать выгорания всего за 5 минут в день
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ===== БРЕНДИНГ И УТП =====
BOT_NAME = 'Tempo'
BOT_VERSION = '4.0'
BOT_DESCRIPTION = 'Найди свой ритм работы и отдыха 🎵'

# 🔥 УНИКАЛЬНОЕ ТОРГОВОЕ ПРЕДЛОЖЕНИЕ (УТП)
USP_TAGLINE = '5 минут в день для профилактики выгорания'
USP_FULL = 'Помоги себе избежать выгорания всего за 5 минут в день 🎵'
USP_SHORT = 'Всего 5 минут — и ты в балансе'

# ===== API КЛЮЧИ =====
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'YOUR_TELEGRAM_TOKEN_HERE')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY_HERE')

# ===== ПУТИ К ФАЙЛАМ =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
AUDIO_DIR = os.path.join(RESOURCES_DIR, 'audio')
PDF_DIR = os.path.join(RESOURCES_DIR, 'pdf')
IMAGES_DIR = os.path.join(RESOURCES_DIR, 'images')
UPLOADS_DIR = os.path.join(BASE_DIR, 'user_uploads')

# ===== 5 АУДИО-ПРАКТИК (все ≤ 5 минут) =====
PRACTICES = {
    'breathing_478': {
        'id': 1,
        'name': '🫁 Дыхательная практика 4-7-8 "Долгий вдох"',
        'audio_file': 'practice_1_breathing_478.mp3',
        'duration': '5 минут',
        'category': 'Экстренная помощь',
        'description': 'Техника дыхания: вдох на 4, задержка на 7, выдох на 8.',
        'benefit': 'Быстро успокаивает, снижает тревожность',
        'when': 'При стрессе, перед важной встречей',
        'icon': '🫁',
        'usp_note': 'Всего 5 минут — и нервная система в балансе'
    },
    'morning_awakening': {
        'id': 2,
        'name': '🌅 Медитация "Мягкое пробуждение"',
        'audio_file': 'practice_2_morning_awakening.mp3',
        'duration': '5 минут',
        'category': 'Утро',
        'description': 'Утренняя медитация для фонового прослушивания.',
        'benefit': 'Гармоничное начало дня без спешки',
        'when': 'Сразу после пробуждения',
        'icon': '🌅',
        'usp_note': '5 минут утром — и день начинается в ресурсе'
    },
    'calm_sleep': {
        'id': 3,
        'name': '🌙 Практика "Спокойный сон"',
        'audio_file': 'practice_3_calm_sleep.mp3',
        'duration': '5 минут',
        'category': 'Вечер',
        'description': 'Мягкая подготовка ко сну, переключение с работы на отдых.',
        'benefit': 'Улучшает качество сна, расслабляет',
        'when': 'За 30-60 минут до сна',
        'icon': '🌙',
        'usp_note': '5 минут вечером — и сон будет глубоким'
    },
    'body_release': {
        'id': 4,
        'name': '💆 Микропаузы "Снять напряжение в теле"',
        'audio_file': 'practice_4_body_release.mp3',
        'duration': '5 минут',
        'category': 'В течение дня',
        'description': 'Телесная практика для снятия зажимов от сидения и стресса.',
        'benefit': 'Снимает физическое напряжение',
        'when': 'Каждый час работы',
        'icon': '💆',
        'usp_note': '5 минут в день — и тело скажет спасибо'
    },
    'deep_focus': {
        'id': 5,
        'name': '🎯 Практика "Глубокий фокус"',
        'audio_file': 'practice_5_deep_focus.mp3',
        'duration': '5 минут',
        'category': 'Работа',
        'description': 'Практика для концентрации и входа в состояние потока.',
        'benefit': 'Улучшает фокус, повышает продуктивность',
        'when': 'Перед важной задачей',
        'icon': '🎯',
        'usp_note': '5 минут настройки — и работа идёт легче'
    }
}

# ===== КАТЕГОРИИ =====
PRACTICE_CATEGORIES = {
    'Утро': ['morning_awakening'],
    'В течение дня': ['body_release', 'deep_focus'],
    'Вечер': ['calm_sleep'],
    'Экстренная помощь': ['breathing_478']
}

# ===== ДНИ НЕДЕЛИ =====
DAYS_RU = {
    'понедельник': 'Monday', 'вторник': 'Tuesday',
    'среда': 'Wednesday', 'четверг': 'Thursday',
    'пятница': 'Friday', 'суббота': 'Saturday', 'воскресенье': 'Sunday'
}
DAYS_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DAYS_RU_FULL = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

# ===== НАСТРОЙКИ AI =====
AI_MODEL = 'gpt-4o'
MAX_FILE_SIZE_MB = 10

# ===== ЛИМИТЫ =====
MAX_HOURS_PER_DAY = 12
MAX_PRACTICE_DURATION = '5 минут'

# ===== НАСТРОЙКИ НАПОМИНАНИЙ =====
REMINDERS_ENABLED_BY_DEFAULT = True
REMINDER_INTERVAL_MINUTES = 120
MAX_REMINDERS_PER_DAY = 6

# ===== СООБЩЕНИЯ С УТП =====
USP_MESSAGES = [
    f"🎵 {USP_SHORT} ✨",
    "5 минут заботы о себе — инвестиция в твой ресурс 💚",
    "Маленькие шаги каждый день = большой результат для ментального здоровья",
    "Не нужно часов медитаций — достаточно 5 минут с Tempo 🎧",
    "Твой анти-выгорание ритуал: всего 5 минут в день"
]

# ===== ЦВЕТА БРЕНДА =====
BRAND_COLORS = {
    'primary': '#FF6D20',      # Оранжевый — энергия, энтузиазм
    'secondary': '#2D8FFF',    # Синий — спокойствие, доверие
    'accent': '#B6FF2F',       # Лайм — свежесть, рост
    'purple': '#AE74FF',       # Фиолетовый — креативность, мудрость
}