import os
import traceback

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import config
from task_manager import add_task, get_tasks_summary, clear_all_tasks

def main_keyboard():
return ReplyKeyboardMarkup([
['📋 Задачи'],
['🎧 Практики'],
['📥 Материалы']
], resize_keyboard=True)

def tasks_keyboard():
return InlineKeyboardMarkup([
[InlineKeyboardButton("➕ Добавить", callback_data="add")],
[InlineKeyboardButton("📄 Список", callback_data="list")],
[InlineKeyboardButton("🧹 Очистить", callback_data="clear")]
])

def practices_keyboard():
return InlineKeyboardMarkup([
[InlineKeyboardButton(p["name"], callback_data=f"p_{k}")]
for k, p in config.PRACTICES.items()
])

async def send_file(bot, chat_id, path, file_type):
print("FILE:", path, os.path.exists(path))

```
if not os.path.exists(path):
    await bot.send_message(chat_id, f"❌ Нет файла:\n{path}")
    return

try:
    with open(path, "rb") as f:
        if file_type == "audio":
            await bot.send_audio(chat_id, f)
        elif file_type == "photo":
            await bot.send_photo(chat_id, f)
        else:
            await bot.send_document(chat_id, f)
except Exception as e:
    print("SEND ERROR:", e)
```

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text("Привет 👋", reply_markup=main_keyboard())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
query = update.callback_query
await query.answer()

```
    data = query.data
    user_id = query.from_user.id

    if data.startswith("p_"):
        key = data.split("_")[1]
        p = config.PRACTICES[key]

        await send_file(context.bot, user_id, os.path.join(config.IMAGES_DIR, p["image"]), "photo")
        await send_file(context.bot, user_id, os.path.join(config.AUDIO_DIR, p["audio"]), "audio")

    elif data == "add":
        context.user_data["step"] = "title"
        await query.message.reply_text("Название задачи:")

    elif data == "list":
        await query.message.reply_text(get_tasks_summary(user_id))

    elif data == "clear":
        clear_all_tasks(user_id)
        await query.message.reply_text("Очищено")

except Exception as e:
    print("BUTTON ERROR:", e)
```

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
msg = update.message.text
user_id = update.effective_user.id

```
    if msg == "📋 Задачи":
        await update.message.reply_text("Меню задач", reply_markup=tasks_keyboard())

    elif msg == "🎧 Практики":
        await update.message.reply_text("Выбери:", reply_markup=practices_keyboard())

    elif msg == "📥 Материалы":
        await send_file(context.bot, user_id, os.path.join(config.PDF_DIR, "guide.pdf"), "doc")

    elif context.user_data.get("step") == "title":
        add_task(user_id, {"title": msg})
        context.user_data.clear()
        await update.message.reply_text("Добавлено")

    else:
        await update.message.reply_text("Используй кнопки")

except Exception as e:
    print("TEXT ERROR:", e)
    await update.message.reply_text(f"Ошибка: {e}")
```

def main():
app = Application.builder().token(config.BOT_TOKEN).build()

```
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

print("🚀 запущен")
app.run_polling()
```

if **name** == "**main**":
main()
