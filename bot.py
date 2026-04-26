"""
🎵 Tempo Bot — Telegram-бот для баланса работы и отдыха
MVP версия
"""

import logging
import os
import sys
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

import config
from task_manager import add_task, get_tasks_summary, clear_all_tasks, get_task_statistics
from reminders import (
    send_reminder, 
    setup_daily_reminders, 
    handle_reminder_callback,
    toggle_reminders
)
from ai_analyzer import analyze_schedule, format_analysis_result, save_analysis_history

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


# ===== КЛАВИАТУРЫ =====

def main_keyboard():
    return ReplyKeyboardMarkup(
        [["📋 Задачи"], ["🎧 Практики"], ["📥 Материалы"]],
        resize_keyboard=True,
    )


def tasks_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить", callback_data="add")],
        [InlineKeyboardButton("📄 Список", callback_data="list")],
        [InlineKeyboardButton("🧹 Очистить", callback_data="clear")],
        [InlineKeyboardButton("🤖 AI-анализ", callback_data="ai_start")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")],
    ])


def practices_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(p["name"], callback_data=f"p_{k}")]
        for k, p in config.PRACTICES.items()
    ])


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

async def send_file(bot, chat_id, path, file_type):
    if not os.path.exists(path):
        logger.warning(f"Файл не найден: {path}")
        await bot.send_message(chat_id, f"⚠️ Файл временно недоступен")
        return False
    
    try:
        with open(path, "rb") as f:
            if file_type == "audio":
                await bot.send_audio(chat_id, f)
            elif file_type == "photo":
                await bot.send_photo(chat_id, f)
            else:
                await bot.send_document(chat_id, f)
        logger.info(f"Файл отправлен: {path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки файла {path}: {e}")
        await bot.send_message(chat_id, "⚠️ Ошибка отправки файла")
        return False


# ===== ОБРАБОТЧИКИ КОМАНД =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Start от пользователя {user.id} ({user.first_name})")
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"🎵 Я — Tempo Bot\n"
        f"{config.USP}\n\n"
        f"Выберите раздел:",
        reply_markup=main_keyboard(),
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        logger.info(f"Callback от {user_id}: {data}")
        
        if data.startswith("p_"):
            key = data.split("_")[1]
            practice = config.PRACTICES.get(key)
            
            if not practice:
                await query.edit_message_text("❌ Практика не найдена")
                return
            
            await query.edit_message_text(
                f"🎧 {practice['name']}\n\n"
                f"⏱️ 5 минут\n"
                f"📝 {practice['desc']}"
            )
            
            image_path = config.IMAGES_DIR / practice["image"]
            audio_path = config.AUDIO_DIR / practice["audio"]
            
            await send_file(context.bot, user_id, image_path, "photo")
            await send_file(context.bot, user_id, audio_path, "audio")
        
        elif data == "add":
            context.user_data["step"] = "title"
            await query.message.reply_text(
                "✏️ Введите название задачи:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data="back")]
                ])
            )
        
        elif data == "list":
            summary = get_tasks_summary(user_id)
            await query.message.reply_text(summary)
        
        elif data == "clear":
            clear_all_tasks(user_id)
            await query.message.reply_text("🧹 Все задачи удалены")
        
        elif data == "stats":
            stats = get_task_statistics(user_id)
            text = (
                f"📊 Ваша статистика:\n\n"
                f"📋 Задач: {stats['total']}\n"
                f"⏱️ Всего часов: {stats['total_hours']}\n\n"
                f"🔴 Высокий приоритет: {stats['by_priority']['high']}\n"
                f"🟡 Средний: {stats['by_priority']['medium']}\n"
                f"🟢 Низкий: {stats['by_priority']['low']}"
            )
            await query.message.reply_text(text)
        
        elif data == "ai_start":
            context.user_data["step"] = "ai_input"
            await query.message.reply_text(
                "🤖 AI-анализ расписания\n\n"
                "Отправьте ваше расписание текстом.\n"
                "Пример:\n"
                "Понедельник: Работа 8ч, Спорт 1ч",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data="back")]
                ])
            )
        
        elif data == "reminder_done" or data == "practices_menu":
            await handle_reminder_callback(update, context)
        
        elif data == "back":
            await query.edit_message_text(
                "🏠 Главное меню:",
                reply_markup=main_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка в handle_buttons: {e}", exc_info=True)
        await update.callback_query.message.reply_text("⚠️ Произошла ошибка")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"Текст от {user_id}: {msg}")
        logger.info(f"Текущий step: {context.user_data.get('step')}")
        
        if msg == "📋 Задачи":
            await update.message.reply_text(
                "📋 Управление задачами:",
                reply_markup=tasks_keyboard(),
            )
        
        elif msg == "🎧 Практики":
            await update.message.reply_text(
                "🎧 Выберите практику восстановления:",
                reply_markup=practices_keyboard(),
            )
        
        elif msg == "📥 Материалы":
            guide_path = config.PDF_DIR / "guide.pdf"
            tracker_path = config.PDF_DIR / "tracker.pdf"
            
            await update.message.reply_text("📥 Отправляю материалы...")
            
            sent = False
            if guide_path.exists():
                await send_file(context.bot, user_id, guide_path, "document")
                sent = True
            if tracker_path.exists():
                await send_file(context.bot, user_id, tracker_path, "document")
                sent = True
            
            if not sent:
                await update.message.reply_text("⏳ Материалы в подготовке. Загляните позже!")
        
        # ===== ДОБАВЛЕНИЕ ЗАДАЧИ =====
        elif context.user_data.get("step") == "title":
            try:
                logger.info(f"Попытка добавить задачу: {msg}")
                
                if len(msg.strip()) < 2:
                    await update.message.reply_text("❌ Название слишком короткое")
                    return
                
                task_data = {
                    "title": msg.strip(),
                    "duration_hours": 1,
                    "day": "Monday",
                    "priority": "medium"
                }
                
                logger.info(f"Данные задачи: {task_data}")
                
                result = add_task(user_id, task_data)
                
                logger.info(f"Результат добавления: {result}")
                
                context.user_data.clear()
                
                await update.message.reply_text(
                    f"{result['message']}\n\n✨ {msg.strip()[:50]}",
                    reply_markup=main_keyboard(),
                )
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении задачи: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Не удалось добавить задачу.\n\n"
                    f"Ошибка: {str(e)}\n\n"
                    f"Попробуйте ещё раз или перезапустите бота /start"
                )
                context.user_data.clear()
        
        # ===== AI-АНАЛИЗ =====
        elif context.user_data.get("step") == "ai_input":
            try:
                if len(msg.strip()) < 20:
                    await update.message.reply_text("❌ Слишком мало данных. Опишите расписание подробнее.")
                    return
                
                await update.message.reply_text("🤖 Анализирую...")
                
                result = analyze_schedule(msg)
                formatted = format_analysis_result(result)
                
                await update.message.reply_text(formatted)
                
                save_analysis_history(user_id, msg, result)
                context.user_data.clear()
                
            except Exception as e:
                logger.error(f"Ошибка AI-анализа: {e}", exc_info=True)
                await update.message.reply_text("❌ Ошибка при анализе. Попробуйте ещё раз.")
                context.user_data.clear()
        
        # ===== УПРАВЛЕНИЕ НАПОМИНАНИЯМИ =====
        elif msg.lower() in ["напоминания вкл", "включить напоминания", "/reminders_on"]:
            toggle_reminders(user_id, True)
            await update.message.reply_text("🔔 Напоминания включены!")
        
        elif msg.lower() in ["напоминания выкл", "выключить напоминания", "/reminders_off"]:
            toggle_reminders(user_id, False)
            await update.message.reply_text("🔕 Напоминания выключены")
        
        else:
            await update.message.reply_text(
                "💡 Используйте кнопки меню для навигации",
                reply_markup=main_keyboard(),
            )
    
    except Exception as e:
        logger.error(f"Критическая ошибка в handle_text: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Произошла ошибка.\n\n"
            f"Детали: {str(e)}\n\n"
            "Попробуйте /start для перезапуска"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте позже."
        )


# ===== ТОЧКА ВХОДА =====

def main():
    logger.info("🎵 Tempo Bot запускается...")
    logger.info(f"BASE_DIR: {config.BASE_DIR}")
    
    if not config.BOT_TOKEN:
        logger.critical("❌ TELEGRAM_TOKEN не найден!")
        print("ERROR: Set TELEGRAM_TOKEN in .env or hosting panel")
        sys.exit(1)
    
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_error_handler(error_handler)
    
    # Настройка напоминаний
    try:
        setup_daily_reminders(application)
        logger.info("✅ Система напоминаний активирована")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось настроить напоминания: {e}")
    
    logger.info("✅ Бот готов к работе")
    print("🚀 Tempo Bot запущен!")
    
    if __name__ == "__main__":
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            timeout=30,
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
