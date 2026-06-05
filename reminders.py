"""
🔔 Tempo Bot — Система напоминаний
"""

import random
import logging
from datetime import datetime, time

import config
from task_manager import load_data, save_data

logger = logging.getLogger(__name__)

REMINDERS = {
    "microbreak": [
        "☕ Отойди от экрана на 2 минуты — глаза скажут спасибо",
        "💧 Выпей стакан воды — организм работает лучше",
        "👀 Посмотри в окно 20 секунд — правило 20-20-20",
        "🚶‍♀️ Встань и пройдись — разгони кровь",
        "🧘‍♀️ Сделай 3 глубоких вдоха — успокой нервную систему"
    ],
    "stretch": [
        "💆 Потянись! Подними руки вверх к потолку",
        "🤸‍♀️ Круговые движения плечами — 5 раз в каждую сторону",
        "🧘 Наклоны головы: медленно вправо-влево, 3 раза",
        "💪 Разомни кисти — сожми и разожми кулаки 10 раз",
        "🦵 Встань и сделай 5 приседаний — тело скажет спасибо"
    ],
    "fresh_air": [
        "🌿 Выйди на улицу на 5 минут — свежий воздух перезагрузит мозг",
        "🪟 Открой окно и подыши 2 минуты",
        "🌳 Посмотри на что-то зелёное — успокаивает глаза",
        "☀️ Если есть солнце — подставь лицо на минуту",
        "🌬️ 5 глубоких вдохов свежим воздухом"
    ],
    "motivation": [
        "✨ Ты молодец! Продолжай заботиться о себе",
        "🌟 5 минут в день — и ты в балансе. Так держать!",
        "💚 Каждая пауза — инвестиция в твоё здоровье",
        "🎵 Tempo гордится тобой! Ты на правильном пути",
        "🌈 Помни: отдых — это часть продуктивности"
    ]
}

REMINDER_SCHEDULE = {
    "morning": {"time": time(10, 0), "types": ["microbreak", "motivation"]},
    "afternoon": {"time": time(14, 0), "types": ["stretch", "fresh_air"]},
    "evening": {"time": time(17, 0), "types": ["microbreak", "motivation"]}
}


def get_random_reminder(category=None):
    if category and category in REMINDERS:
        return random.choice(REMINDERS[category])
    
    all_reminders = []
    for reminders in REMINDERS.values():
        all_reminders.extend(reminders)
    return random.choice(all_reminders)


def get_reminder_by_time():
    current_hour = datetime.now().hour
    
    if 9 <= current_hour < 12:
        category = random.choice(["microbreak", "motivation"])
    elif 12 <= current_hour < 15:
        category = random.choice(["stretch", "fresh_air"])
    elif 15 <= current_hour < 18:
        category = random.choice(["microbreak", "motivation"])
    else:
        category = "motivation"
    
    return get_random_reminder(category), category


def is_reminder_enabled(user_id):
    data = load_data()
    user_id = str(user_id)
    
    if user_id not in data["users"]:
        return True
    
    settings = data["users"][user_id].get("settings", {})
    return settings.get("reminders_enabled", True)


def toggle_reminders(user_id, enable):
    data = load_data()
    user_id = str(user_id)
    
    if user_id not in data["users"]:
        data["users"][user_id] = {"settings": {}}
    
    if "settings" not in data["users"][user_id]:
        data["users"][user_id]["settings"] = {}
    
    data["users"][user_id]["settings"]["reminders_enabled"] = enable
    save_data(data)
    
    logger.info(f"Напоминания для {user_id}: {'включены' if enable else 'выключены'}")
    return True


def get_reminder_icon(category):
    icons = {
        "microbreak": "☕",
        "stretch": "🧘‍♀️",
        "fresh_air": "🌿",
        "motivation": "✨"
    }
    return icons.get(category, "🔔")


def format_reminder_message(reminder_text, category):
    icon = get_reminder_icon(category)
    return f"{icon} {reminder_text}\n\n{config.USP}"


async def send_reminder(bot, user_id, context=None):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if not is_reminder_enabled(user_id):
        logger.debug(f"Напоминания отключены для {user_id}")
        return False
    
    reminder_text, category = get_reminder_by_time()
    message = format_reminder_message(reminder_text, category)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Сделал!", callback_data="reminder_done")],
        [InlineKeyboardButton("🎧 Практика", callback_data="practices_menu")]
    ])
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=keyboard
        )
        logger.info(f"Напоминание отправлено пользователю {user_id}")
        
        data = load_data()
        user_id_str = str(user_id)
        
        if user_id_str in data["users"]:
            stats = data["users"][user_id_str].get("stats", {})
            stats["reminders_sent"] = stats.get("reminders_sent", 0) + 1
            data["users"][user_id_str]["stats"] = stats
            save_data(data)
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания {user_id}: {e}")
        return False


def setup_daily_reminders(application):
    from telegram.ext import JobQueue
    
    job_queue = application.job_queue
    
    if not job_queue:
        logger.warning("JobQueue не доступен — напоминания отключены")
        return
    
    logger.info("🔔 Настройка ежедневных напоминаний...")
    
    for period_name, schedule in REMINDER_SCHEDULE.items():
        try:
            job_queue.run_daily(
                callback=_daily_reminder_job,
                time=schedule["time"],
                name=f"tempo_reminder_{period_name}",
                data={"period": period_name}
            )
            logger.info(f"✅ Напоминание {period_name} на {schedule['time']}")
        except Exception as e:
            logger.error(f"Ошибка настройки напоминания {period_name}: {e}")


async def _daily_reminder_job(context):
    try:
        data = load_data()
        period = context.job.data.get("period", "unknown")
        
        logger.info(f"🔔 Запуск напоминаний ({period}) для {len(data.get('users', {}))} пользователей")
        
        for user_id in data.get("users", {}).keys():
            try:
                if is_reminder_enabled(user_id):
                    await send_reminder(context.bot, int(user_id), context)
            except Exception as e:
                logger.error(f"Ошибка напоминания для {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка в _daily_reminder_job: {e}")


async def handle_reminder_callback(update, context):
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"Callback напоминания от {user_id}: {data}")
    
    if data == "reminder_done":
        data_store = load_data()
        user_id_str = str(user_id)
        
        if user_id_str in data_store["users"]:
            stats = data_store["users"][user_id_str].get("stats", {})
            stats["reminders_completed"] = stats.get("reminders_completed", 0) + 1
            data_store["users"][user_id_str]["stats"] = stats
            save_data(data_store)
        
        await query.edit_message_text(
            f"👏 Отлично! Забота о себе — это важно.\n\n{config.USP}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎧 Ещё практика", callback_data="practices_menu")]
            ])
        )
    
    elif data == "practices_menu":
        from bot import practices_keyboard
        await query.edit_message_text(
            "🎧 Выберите практику восстановления:",
            reply_markup=practices_keyboard()
        )
