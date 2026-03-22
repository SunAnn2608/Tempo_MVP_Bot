import os
import traceback

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

import config
from task_manager import *
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


# ===== ERROR HANDLER =====

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("ERROR:", context.error)
    traceback.print_exc()

    try:
        chat_id = update.effective_chat.id
        img = os.path.join(config.IMAGES_DIR, "error.png")

        text = "🎵 Tempo временно недоступен\nМы уже всё чиним 💚"

        if os.path.exists(img):
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(img),
                caption=text
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=text)

    except Exception as e:
        print("error handler failed:", e)


# ===== START =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    schedule_reminders(context.application, user.id)

    img = os.path.join(config.IMAGES_DIR, "start.png")

    text = (
        f"Привет, {user.first_name} 👋\n\n"
        "Я помогу тебе не выгореть и навести порядок в задачах.\n\n"
        "Как ты себя чувствуешь сейчас?"
    )

    if os.path.exists(img):
        await update.message.reply_photo(
            photo=InputFile(img),
            caption=text,
            reply_markup=mood_keyboard()
        )
    else:
        await update.message.reply_text(text, reply_markup=mood_keyboard())


# ===== CALLBACK =====

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # ===== ПРАКТИКИ =====
    if data.startswith("p_"):
        key = data.split("_")[1]
        practice = config.PRACTICES.get(key)

        if not practice:
            await query.message.reply_text("❌ Практика не найдена")
            return

        image_path = os.path.join(config.IMAGES_DIR, practice["image"])
        audio_path = os.path.join(config.AUDIO_DIR, practice["audio"])

        print("IMAGE:", image_path, os.path.exists(image_path))
        print("AUDIO:", audio_path, os.path.exists(audio_path))

        # КАРТИНКА
        if os.path.exists(image_path):
            await context.bot.send_photo(
                chat_id=user_id,
                photo=InputFile(image_path),
                caption=f"{practice['name']}\n\n🎧 Практика на 5 минут"
            )
        else:
            await query.message.reply_text("⚠️ Картинка не найдена")

        # АУДИО (MP3)
        if os.path.exists(audio_path):
            try:
                await context.bot.send_audio(
                    chat_id=user_id,
                    audio=InputFile(audio_path),
                    title=practice["name"]
                )
            except Exception as e:
                print("AUDIO ERROR:", e)
                await query.message.reply_text("⚠️ Не удалось отправить аудио")
        else:
            await query.message.reply_text("⚠️ Аудио не найдено")

    # ===== PDF =====
    elif data == "tracker":
        await context.bot.send_document(
            chat_id=user_id,
            document=InputFile(os.path.join(config.PDF_DIR, "tracker.pdf"))
        )

    elif data == "guide":
        await context.bot.send_document(
            chat_id=user_id,
            document=InputFile(os.path.join(config.PDF_DIR, "guide.pdf"))
        )

    # ===== TASKS =====
    elif data == "add_task":
        context.user_data["step"] = "title"
        await query.message.reply_text("Введите название задачи:")

    elif data == "list_tasks":
        await query.message.reply_text(get_tasks_summary(user_id))

    elif data == "clear_tasks":
        clear_all_tasks(user_id)
        await query.message.reply_text("🧹 Все задачи удалены")

    elif data == "back":
        await query.message.reply_text("Меню", reply_markup=main_keyboard())


# ===== TEXT =====

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id

    step = context.user_data.get("step")

    if msg in ["😌 Спокойно", "😐 Нормально", "😣 Перегруз"]:
        await update.message.reply_text("Ок, давай работать", reply_markup=main_keyboard())
        return

    if step == "title":
        context.user_data["title"] = msg
        context.user_data["step"] = "day"
        await update.message.reply_text("Введите день (например Monday):")
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
        await update.message.reply_text("✅ Задача добавлена", reply_markup=main_keyboard())
        return

    if msg == "📋 Задачи":
        await update.message.reply_text("Управление задачами:", reply_markup=tasks_keyboard())

    elif msg == "🎧 Практики":
        await update.message.reply_text("Выбери практику:", reply_markup=practices_keyboard())

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

    print("🚀 бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()