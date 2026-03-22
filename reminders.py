"""
🔔 Tempo Bot — Система напоминаний
"""

import random
from datetime import datetime, time
from telegram.ext import JobQueue

REMINDERS = {
    'microbreak': [
        "☕ Время для микро-паузы! Отойди от экрана на 2 минуты",
        "🧘‍♀️ Сделай глубокий вдох и выдох. Ты молодец!",
        "💧 Выпей стакан воды — организм скажет спасибо",
        "👀 Посмотри в окно 20 секунд — дай глазам отдых",
        "🚶‍♀️ Встань и пройдись по комнате — разгони кровь"
    ],
    'stretch': [
        "💆 Потянись! Подними руки вверх и потянись к потолку",
        "🤸‍♀️ Сделай круговые движения плечами — 5 раз в каждую сторону",
        "🧘 Наклоны головы: медленно вправо-влево, 3 раза",
        "💪 Разомни кисти рук — сожми и разожми кулаки 10 раз",
        "🦵 Встань и сделай 5 приседаний — тело скажет спасибо"
    ],
    'fresh_air': [
        "🌿 Выйди на улицу на 5 минут — свежий воздух перезагрузит мозг",
        "🪟 Открой окно и подыши свежим воздухом 2 минуты",
        "🌳 Посмотри на что-то зелёное — это успокаивает глаза",
        "☀️ Если есть солнце — подставь лицо на минуту",
        "🌬️ Сделай 5 глубоких вдохов свежим воздухом"
    ],
    'water': [
        "💧 Время попить воды! Стакан рядом?",
        "🥤 Гидратация — залог энергии. Выпей воды!",
        "💦 Твоему организму нужна вода. Сделай несколько глотков",
        "🚰 Поставь напоминание пить воду каждый час",
        "🌊 Вода помогает мозгу работать лучше. Попей сейчас!"
    ],
    'motivation': [
        "✨ Ты молодец! Продолжай заботиться о себе",
        "🌟 5 минут в день — и ты в балансе. Так держать!",
        "💚 Каждая микро-пауза — это инвестиция в твоё здоровье",
        "🎵 Tempo гордится тобой! Ты на правильном пути",
        "🌈 Помни: отдых — это часть продуктивности"
    ]
}

REMINDER_SCHEDULE = {
    'morning': {'time': time(10, 0), 'types': ['microbreak', 'water', 'motivation']},
    'afternoon': {'time': time(14, 0), 'types': ['stretch', 'fresh_air']},
    'evening': {'time': time(17, 0), 'types': ['microbreak', 'water', 'motivation']}
}


def get_random_reminder(category: str = None) -> str:
    """Получение случайного напоминания"""
    if category and category in REMINDERS:
        return random.choice(REMINDERS[category])
    else:
        all_reminders = []
        for reminders in REMINDERS.values():
            all_reminders.extend(reminders)
        return random.choice(all_reminders)


def get_reminder_by_time() -> tuple:
    """Напоминание по времени суток"""
    current_hour = datetime.now().hour
    
    if 9 <= current_hour < 12:
        category = random.choice(['microbreak', 'water', 'motivation'])
    elif 12 <= current_hour < 15:
        category = random.choice(['stretch', 'fresh_air'])
    elif 15 <= current_hour < 18:
        category = random.choice(['microbreak', 'water', 'motivation'])
    else:
        category = 'motivation'
    
    return get_random_reminder(category), category