import random
from datetime import datetime, timedelta

import config


# ===== НАСТРОЙКИ =====

START_HOUR = 8
END_HOUR = 22
INTERVAL_MINUTES = 45 # можно менять


# ===== ТЕКСТЫ =====

REMINDERS = {
    'microbreak': [
        "☕ Сделай микро-паузу на пару минут",
        "🧘‍♀️ Сделай глубокий вдох и выдох",
        "👀 Дай глазам отдохнуть — посмотри вдаль",
        "🚶‍♀️ Встань и немного пройдись"
    ],
    'stretch': [
        "💆 Потянись — тело скажет спасибо",
        "🤸‍♀️ Разомни плечи и шею",
        "🧘 Сделай пару лёгких движений"
    ],
    'fresh_air': [
        "🌿 Выйди на свежий воздух на пару минут",
        "🪟 Открой окно и подыши",
        "🌳 Посмотри на что-то зелёное"
    ],
    'water': [
        "💧 Выпей воды",
        "🥤 Гидратация = энергия",
        "🌊 Попей воды прямо сейчас"
    ],
    'motivation': [
        "✨ Ты хорошо справляешься",
        "💚 Маленькие паузы — большой результат",
        "🎵 Ты в процессе — и это уже круто"
    ]
}


# ===== ЛОГИКА =====

def get_random_reminder():
    category = random.choice(list(REMINDERS.keys()))
    return random.choice(REMINDERS[category])


def is_allowed_time(user_hour: int) -> bool:
    return START_HOUR <= user_hour < END_HOUR


# ===== РЕГУЛЯРНАЯ ЗАДАЧА =====

async def send_reminder(context):
    job = context.job
    user_id = job.chat_id

    now = datetime.now()
    hour = now.hour

    if not is_allowed_time(hour):
        return

    text = get_random_reminder()

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{text}\n\n🎵 Не забывай отдыхать"
        )
    except:
        pass


# ===== ЗАПУСК РАСПИСАНИЯ =====

def schedule_reminders(application, user_id):
    """
    Запускает напоминания каждые N минут
    """

    job_queue = application.job_queue

    # удаляем старые задачи (если есть)
    current_jobs = job_queue.get_jobs_by_name(str(user_id))
    for job in current_jobs:
        job.schedule_removal()

    # запускаем новую
    job_queue.run_repeating(
        send_reminder,
        interval=timedelta(minutes=INTERVAL_MINUTES),
        first=10,
        chat_id=user_id,
        name=str(user_id)
    )