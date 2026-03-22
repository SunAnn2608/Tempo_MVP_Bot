import os
from collections import defaultdict

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import config
from task_manager import (
    add_task, get_user_tasks, get_task,
    delete_task, edit_task, mark_task_completed,
    get_tasks_summary, clear_all_tasks
)
from ai_analyzer import extract_tasks_from_text, redistribute_tasks, ai_workload_advice


# ===== КНОПКИ =====

def main_keyboard():
    return ReplyKeyboardMarkup([
        ['📋 Задачи'],
        ['🎧 Практики'],
        ['📥 Материалы'],
        ['📊 Статистика']
    ], resize_keyboard=True)


def mood_keyboard():
    return ReplyKeyboardMarkup([
        ['😌 Спокойно', '😐 Нормально', '😣 Перегруз']
    ], resize_keyboard=True)


def tasks_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить задачу", callback_data="add_task")],
        [InlineKeyboardButton("📄 Список задач", callback_data="list_tasks")],
        [InlineKeyboardButton("🧹 Очистить всё", callback_data="clear_tasks")]
    ])


def practices_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(p["name"], callback_data=f"p_{k}")]
        for k, p in config.PRACTICES.items()
    ] + [[InlineKeyboardButton("🔙 Назад", callback_data="back")]])


def resources_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Трекер", callback_data="tracker")],
        [InlineKeyboardButton("📖 Методичка", callback_data="guide")]
    ])


def tasks_list_keyboard(tasks):
    keyboard = []
    for t in tasks.values():
        keyboard.append([
            InlineKeyboardButton(
                f"#{t['id']} {t['title'][:20]}",
                callback_data=f"task_{t['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def task_actions_keyboard(task_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Завершить", callback_data=f"done_{task_id}")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{task_id}")],
        [InlineKeyboardButton("📅 Перенести", callback_data=f"move_{task_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{task_id}")]
    ])


# ===== АНАЛИЗ НАГРУЗКИ =====

def calculate_workload(tasks):
    days = defaultdict(int)

    for t in tasks.values():
        days[t.get('day', 'Unknown')] += 1

    overload_days = sum(1 for c in days.values() if c > config.MAX_TASKS_PER_DAY)
    total_days = len(days) if days else 1

    ratio = overload_days / total_days
    burnout_risk = int(min(100, ratio * 100 + (len(tasks) * 2)))

    if burnout_risk > 70:
        level = "🔴 высокий"
    elif burnout_risk > 40:
        level = "🟡 средний"
    else:
        level = "🟢 низкий"

    return burnout_risk, level


# ===== СТАРТ =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    img = os.path.join(config.IMAGES_DIR, "start.png")

    text = (
        f"Привет, {user.first_name} 👋\n\n"
        "Я помогаю навести порядок в задачах\n"
        "и не выгореть по дороге.\n\n"
        "Мы будем двигаться маленькими шагами —\n"
        "без перегрузки и давления.\n\n"
        "Давай начнём.\n\n"
        "Как ты сейчас себя чувствуешь?"
    )

    if os.path.exists(img):
        await update.message.reply_photo(
            photo=open(img, "rb"),
            caption=text,
            reply_markup=mood_keyboard()
        )
    else:
        await update.message.reply_text(text, reply_markup=mood_keyboard())


# ===== КНОПКИ =====

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # ===== ПРАКТИКИ =====
    if data.startswith("p_"):
        key = data.split("_")[1]
        p = config.PRACTICES[key]

        img = os.path.join(config.IMAGES_DIR, p["image"])
        audio = os.path.join(config.AUDIO_DIR, p["audio"])

        if os.path.exists(img):
            await query.message.reply_photo(photo=open(img, "rb"))

        if os.path.exists(audio):
            await context.bot.send_voice(chat_id=user_id, voice=open(audio, "rb"))

    # ===== PDF =====
    elif data == "tracker":
        await context.bot.send_document(
            chat_id=user_id,
            document=open(os.path.join(config.PDF_DIR, "tracker.pdf"), "rb")
        )

    elif data == "guide":
        await context.bot.send_document(
            chat_id=user_id,
            document=open(os.path.join(config.PDF_DIR, "guide.pdf"), "rb")
        )

    # ===== ЗАДАЧИ =====
    elif data == "list_tasks":
        tasks = get_user_tasks(user_id)
        await query.message.reply_text("📋 Задачи:", reply_markup=tasks_list_keyboard(tasks))

    elif data.startswith("task_"):
        task_id = int(data.split("_")[1])
        task = get_task(user_id, task_id)

        await query.message.reply_text(
            f"{task['title']}\n⏱ {task['duration_hours']}ч\n📅 {task['day']}",
            reply_markup=task_actions_keyboard(task_id)
        )

    elif data.startswith("done_"):
        mark_task_completed(user_id, int(data.split("_")[1]))
        await query.message.reply_text("✅ Выполнено")

    elif data.startswith("delete_"):
        delete_task(user_id, int(data.split("_")[1]))
        await query.message.reply_text("🗑 Удалено")

    elif data.startswith("move_"):
        task_id = int(data.split("_")[1])
        days = config.DAYS_EN

        keyboard = [[InlineKeyboardButton(d, callback_data=f"moveto_{d}_{task_id}")] for d in days]
        await query.message.reply_text("Выбери день:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("moveto_"):
        _, day, task_id = data.split("_")
        edit_task(user_id, int(task_id), {'day': day})
        await query.message.reply_text("📅 Перенесено")

    elif data == "clear_tasks":
        clear_all_tasks(user_id)
        await query.message.reply_text("🧹 Очищено")

    elif data == "add_task":
        context.user_data["step"] = "title"
        await query.message.reply_text("Название задачи:")

    elif data == "back":
        await query.message.reply_text("Меню", reply_markup=main_keyboard())


# ===== ТЕКСТ =====

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id

    step = context.user_data.get("step")

    # ===== ОНБОРДИНГ =====
    if msg == "😣 Перегруз":
        await update.message.reply_text(
            "Похоже, у тебя сейчас перегруз.\n"
            "Давай попробуем разобрать задачи и упростить план.",
            reply_markup=main_keyboard()
        )
        return

    if msg == "😐 Нормально":
        await update.message.reply_text(
            "Отлично, давай посмотрим твои задачи и наведём порядок 👌",
            reply_markup=main_keyboard()
        )
        return

    if msg == "😌 Спокойно":
        await update.message.reply_text(
            "Класс! Тогда давай спланируем задачи так, чтобы сохранить это состояние ✨",
            reply_markup=main_keyboard()
        )
        return

    # ===== ДИАЛОГ ДОБАВЛЕНИЯ =====
    if step == "title":
        context.user_data["title"] = msg
        context.user_data["step"] = "day"
        await update.message.reply_text("День (Monday):")
        return

    if step == "day":
        context.user_data["day"] = msg
        context.user_data["step"] = "duration"
        await update.message.reply_text("Сколько часов?")
        return

    if step == "duration":
        try:
            duration = float(msg)
        except:
            await update.message.reply_text("Введите число")
            return

        add_task(user_id, {
            "title": context.user_data["title"],
            "day": context.user_data["day"],
            "duration_hours": duration
        })

        context.user_data.clear()
        await update.message.reply_text("✅ Добавлено", reply_markup=main_keyboard())
        return

    # ===== МЕНЮ =====
    if msg == "📋 Задачи":
        await update.message.reply_text("Управление задачами:", reply_markup=tasks_keyboard())

    elif msg == "🎧 Практики":
        await update.message.reply_text("Выбери:", reply_markup=practices_keyboard())

    elif msg == "📥 Материалы":
        await update.message.reply_text("Материалы:", reply_markup=resources_keyboard())

    elif msg == "📊 Статистика":
        tasks = get_user_tasks(user_id)

        risk, level = calculate_workload(tasks)
        advice = ai_workload_advice(get_tasks_summary(user_id))

        await update.message.reply_text(
            f"📊 Нагрузка:\n\n"
            f"Риск выгорания: {risk}%\n"
            f"Уровень: {level}\n\n"
            f"{advice}"
        )

    else:
        tasks = extract_tasks_from_text(msg)

        if tasks:
            total = sum(t['duration_hours'] for t in tasks)

            if total > config.MAX_HOURS_PER_DAY:
                tasks = redistribute_tasks(tasks)
                await update.message.reply_text("⚠️ Перегруз — распределил задачи")

            for t in tasks:
                add_task(user_id, t)

            await update.message.reply_text("✅ Добавлено")
        else:
            add_task(user_id, {"title": msg})
            await update.message.reply_text("✅ Задача добавлена")


# ===== MAIN =====

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    print("бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()