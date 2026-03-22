import os
import traceback
from collections import defaultdict

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import config
from task_manager import *
from ai_analyzer import *
from reminders import schedule_reminders


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


# ===== ОШИБКА =====

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Ошибка:", context.error)
    traceback.print_exc()

    try:
        chat_id = update.effective_chat.id

        img = os.path.join(config.IMAGES_DIR, "error.png")

        text = "🎵 Tempo временно недоступен\nМы уже всё чиним 💚"

        if os.path.exists(img):
            await context.bot.send_photo(chat_id=chat_id, photo=open(img, "rb"), caption=text)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text)

    except Exception as e:
        print("error handler failed:", e)


# ===== СТАРТ =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    schedule_reminders(context.application, user.id)

    img = os.path.join(config.IMAGES_DIR, "start.png")

    text = (
        f"Привет, {user.first_name} 👋\n\n"
        "Я помогаю навести порядок в задачах\n"
        "и не выгореть по дороге.\n\n"
        "Как ты сейчас себя чувствуешь?"
    )

    if os.path.exists(img):
        await update.message.reply_photo(photo=open(img, "rb"), caption=text, reply_markup=mood_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=mood_keyboard())


# ===== КНОПКИ =====

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data.startswith("p_"):
        p = config.PRACTICES[data.split("_")[1]]

        await query.message.reply_photo(
            photo=open(os.path.join(config.IMAGES_DIR, p["image"]), "rb")
        )

        await context.bot.send_voice(
            chat_id=user_id,
            voice=open(os.path.join(config.AUDIO_DIR, p["audio"]), "rb")
        )

    elif data == "tracker":
        await context.bot.send_document(chat_id=user_id, document=open(os.path.join(config.PDF_DIR, "tracker.pdf"), "rb"))

    elif data == "guide":
        await context.bot.send_document(chat_id=user_id, document=open(os.path.join(config.PDF_DIR, "guide.pdf"), "rb"))

    elif data == "add_task":
        context.user_data["step"] = "title"
        await query.message.reply_text("Название задачи:")

    elif data == "list_tasks":
        tasks = get_user_tasks(user_id)
        text = get_tasks_summary(user_id)
        await query.message.reply_text(text)

    elif data == "clear_tasks":
        clear_all_tasks(user_id)
        await query.message.reply_text("🧹 Очищено")

    elif data == "back":
        await query.message.reply_text("Меню", reply_markup=main_keyboard())


# ===== ТЕКСТ =====

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id

    step = context.user_data.get("step")

    if msg == "😣 Перегруз":
        await update.message.reply_text("Давай снизим нагрузку", reply_markup=main_keyboard())
        return

    if msg == "😐 Нормально":
        await update.message.reply_text("Ок, посмотрим задачи", reply_markup=main_keyboard())
        return

    if msg == "😌 Спокойно":
        await update.message.reply_text("Супер, закрепим баланс", reply_markup=main_keyboard())
        return

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
        add_task(user_id, {
            "title": context.user_data["title"],
            "day": context.user_data["day"],
            "duration_hours": msg
        })

        context.user_data.clear()
        await update.message.reply_text("✅ Добавлено", reply_markup=main_keyboard())
        return

    if msg == "📋 Задачи":
        await update.message.reply_text("Управление:", reply_markup=tasks_keyboard())

    elif msg == "🎧 Практики":
        await update.message.reply_text("Выбери:", reply_markup=practices_keyboard())

    elif msg == "📥 Материалы":
        await update.message.reply_text("Материалы:", reply_markup=resources_keyboard())

    elif msg == "📊 Статистика":
        await update.message.reply_text("📊 Всё под контролем")

    else:
        add_task(user_id, {"title": msg})
        await update.message.reply_text("Добавлено")


# ===== MAIN =====

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    app.add_error_handler(error_handler)

    print("бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()