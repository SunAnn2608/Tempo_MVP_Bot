import os
import traceback

from telegram import (
Update,
ReplyKeyboardMarkup,
InlineKeyboardButton,
InlineKeyboardMarkup
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
from task_manager import add_task, get_tasks_summary, clear_all_tasks

# ===== КНОПКИ =====

def main_keyboard():
return ReplyKeyboardMarkup([
['📋 Задачи'],
['🎧 Практики'],
['📥 Материалы'],
['📊 Статистика']
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

def days_keyboard():
return ReplyKeyboardMarkup([
['Monday', 'Tuesday'],
['Wednesday', 'Thursday'],
['Friday', 'Saturday'],
['Sunday']
], resize_keyboard=True)

# ===== ОТПРАВКА ФАЙЛОВ =====

async def send_file_safe(bot, chat_id, path, file_type="document", caption=None):
print("SEND FILE:", path, os.path.exists(path))

```
if not os.path.exists(path):
    await bot.send_message(chat_id=chat_id, text=f"❌ Файл не найден:\n{path}")
    return

try:
    with open(path, "rb") as f:
        if file_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=f, caption=caption)

        elif file_type == "audio":
            await bot.send_audio(chat_id=chat_id, audio=f)

        else:
            await bot.send_document(chat_id=chat_id, document=f)

except Exception as e:
    print("FILE ERROR:", e)
    await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка при отправке файла:\n{e}")
```

# ===== START =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"Привет 👋 Я помогу тебе управлять задачами без перегруза",
reply_markup=main_keyboard()
)

# ===== CALLBACK =====

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
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

    await send_file_safe(
        context.bot,
        user_id,
        image_path,
        "photo",
        f"{practice['name']}\n\n🎧 Практика"
    )

    await send_file_safe(context.bot, user_id, audio_path, "audio")

# ===== PDF =====
elif data == "tracker":
    pdf_path = os.path.join(config.PDF_DIR, "tracker.pdf")
    await send_file_safe(context.bot, user_id, pdf_path, "document")

elif data == "guide":
    pdf_path = os.path.join(config.PDF_DIR, "guide.pdf")
    await send_file_safe(context.bot, user_id, pdf_path, "document")

# ===== TASKS =====
elif data == "add_task":
    context.user_data["step"] = "title"
    await query.message.reply_text("Введите название задачи:")
    return

elif data == "list_tasks":
    await query.message.reply_text(get_tasks_summary(user_id))
    return

elif data == "clear_tasks":
    clear_all_tasks(user_id)
    await query.message.reply_text("🧹 Все задачи удалены")
    return

elif data == "back":
    await query.message.reply_text("Меню", reply_markup=main_keyboard())
```

# ===== TEXT =====

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
msg = update.message.text
user_id = update.effective_user.id

```
step = context.user_data.get("step")

# ===== СОЗДАНИЕ ЗАДАЧИ =====
if step == "title":
    context.user_data["title"] = msg
    context.user_data["step"] = "day"
    await update.message.reply_text("Выбери день:", reply_markup=days_keyboard())
    return

if step == "day":
    context.user_data["day"] = msg
    context.user_data["step"] = "duration"
    await update.message.reply_text("Сколько часов займет?")
    return

if step == "duration":
    try:
        duration = float(msg)
    except:
        await update.message.reply_text("Введи число часов (например 2)")
        return

    res = add_task(user_id, {
        "title": context.user_data["title"],
        "day": context.user_data["day"],
        "duration_hours": duration
    })

    context.user_data.clear()

    await update.message.reply_text(
        res.get("message", "Задача добавлена"),
        reply_markup=main_keyboard()
    )
    return

# ===== ОСНОВНОЕ МЕНЮ =====
if msg == "📋 Задачи":
    await update.message.reply_text("Управление задачами:", reply_markup=tasks_keyboard())

elif msg == "🎧 Практики":
    await update.message.reply_text("Выбери практику:", reply_markup=practices_keyboard())

elif msg == "📥 Материалы":
    await update.message.reply_text("Материалы:", reply_markup=resources_keyboard())

elif msg == "📊 Статистика":
    await update.message.reply_text("📊 В разработке 🚧")

else:
    await update.message.reply_text("Не понял 🤔 Используй кнопки меню")
```

# ===== ERROR HANDLER =====

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
print("ERROR:", context.error)
traceback.print_exc()

# ===== MAIN =====

def main():
app = Application.builder().token(config.BOT_TOKEN).build()

```
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

app.add_error_handler(error_handler)

print("🚀 бот запущен")
app.run_polling()
```

if **name** == "**main**":
main()
