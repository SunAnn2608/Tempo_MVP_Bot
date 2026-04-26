"""
🎵 Tempo Bot — Telegram-бот для баланса работы и отдыха
Исправленная версия для bothost.ru и локального запуска

ТРЕБОВАНИЯ ПРОЕКТА:
✅ 1. Условия — if/else валидации и маршрутизации
✅ 2. Словари — PRACTICES, user_data, настройки
✅ 3. Функции — модульная архитектура
✅ 4. Файлы — JSON, аудио, изображения, PDF
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
    """Главное меню (ReplyKeyboard)"""
    return ReplyKeyboardMarkup(
        [["📋 Задачи"], ["🎧 Практики"], ["📥 Материалы"]],
        resize_keyboard=True,
    )


def tasks_keyboard():
    """Меню задач (InlineKeyboard)"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить", callback_data="add")],
        [InlineKeyboardButton("📄 Список", callback_data="list")],
        [InlineKeyboardButton("🧹 Очистить", callback_data="clear")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")],
    ])


def practices_keyboard():
    """Меню практик (InlineKeyboard)"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(p["name"], callback_data=f"p_{k}")]
        for k, p in config.PRACTICES.items()
    ])


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

async def send_file(bot, chat_id, path, file_type):
    """Отправка файла с проверкой существования (ТРЕБОВАНИЕ 1+4)"""
    # ===== ТРЕБОВАНИЕ 1: УСЛОВИЯ =====
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
            else:  # document
                await bot.send_document(chat_id, f)
        logger.info(f"Файл отправлен: {path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки файла {path}: {e}")
        await bot.send_message(chat_id, "⚠️ Ошибка отправки файла")
        return False


# ===== ОБРАБОТЧИКИ КОМАНД =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — приветствие"""
    user = update.effective_user
    logger.info(f"Start от пользователя {user.id} ({user.first_name})")
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"🎵 Я — Tempo Bot\n"
        f"✨ 5 минут в день для профилактики выгорания\n\n"
        f"Выберите раздел:",
        reply_markup=main_keyboard(),
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline-кнопок (ТРЕБОВАНИЕ 1: УСЛОВИЯ)"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        logger.info(f"Callback от {user_id}: {data}")
        
        # ===== ТРЕБОВАНИЕ 1: МАРШРУТИЗАЦИЯ ПО УСЛОВИЯМ =====
        if data.startswith("p_"):
            # ===== ПРАКТИКИ =====
            key = data.split("_")[1]
            practice = config.PRACTICES.get(key)
            
            # ===== УСЛОВИЕ: проверка существования практики =====
            if not practice:
                await query.edit_message_text("❌ Практика не найдена")
                return
            
            # Отправляем карточку и аудио
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
            # ===== ДОБАВЛЕНИЕ ЗАДАЧИ =====
            context.user_data["step"] = "title"
            await query.message.reply_text(
                "✏️ Введите название задачи:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Отмена", callback_data="back")]
                ])
            )
        
        elif data == "list":
            # ===== СПИСОК ЗАДАЧ =====
            summary = get_tasks_summary(user_id)
            await query.message.reply_text(summary)
        
        elif data == "clear":
            # ===== ОЧИСТКА ЗАДАЧ =====
            clear_all_tasks(user_id)
            await query.message.reply_text("🧹 Все задачи удалены")
        
        elif data == "back":
            # ===== ВОЗВРАТ В ГЛАВНОЕ МЕНЮ =====
            await query.edit_message_text(
                "🏠 Главное меню:",
                reply_markup=main_keyboard()
            )
        
        elif data == "stats":
            # ===== СТАТИСТИКА =====
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
    
    except Exception as e:
        logger.error(f"Ошибка в handle_buttons: {e}", exc_info=True)
        await update.callback_query.message.reply_text("⚠️ Произошла ошибка")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (ТРЕБОВАНИЕ 1: УСЛОВИЯ)"""
    try:
        msg = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"Текст от {user_id}: {msg}")
        
        # ===== ТРЕБОВАНИЕ 1: РЕАКЦИЯ НА КНОПКИ МЕНЮ =====
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
            # ===== ОТПРАВКА МАТЕРИАЛОВ =====
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
                await update.message.reply_text(
                    "⏳ Материалы в подготовке. Загляните позже!"
                )
        
        # ===== ТРЕБОВАНИЕ 1: ОБРАБОТКА ВВОДА ЗАДАЧИ =====
        elif context.user_data.get("step") == "title":
            # ===== УСЛОВИЕ: валидация ввода =====
            if len(msg.strip()) < 2:
                await update.message.reply_text("❌ Название слишком короткое")
                return
            
            result = add_task(user_id, {"title": msg.strip()})
            context.user_data.clear()
            
            await update.message.reply_text(
                f"{result['message']}\n\n✨ {msg.strip()[:30]}...",
                reply_markup=main_keyboard(),
            )
        
        else:
            # ===== НЕИЗВЕСТНАЯ КОМАНДА =====
            await update.message.reply_text(
                "💡 Используйте кнопки меню для навигации",
                reply_markup=main_keyboard(),
            )
    
    except Exception as e:
        logger.error(f"Ошибка в handle_text: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте ещё раз.")


# ===== ОБРАБОТЧИК ОШИБОК =====

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте позже.\n"
            "Если проблема повторяется — напишите разработчикам."
        )


# ===== ТОЧКА ВХОДА =====

def main():
    """Запуск бота (ТРЕБОВАНИЕ 3: ФУНКЦИИ)"""
    logger.info("🎵 Tempo Bot запускается...")
    logger.info(f"BASE_DIR: {config.BASE_DIR}")
    logger.info(f"AUDIO_DIR exists: {config.AUDIO_DIR.exists()}")
    logger.info(f"IMAGES_DIR exists: {config.IMAGES_DIR.exists()}")
    logger.info(f"PDF_DIR exists: {config.PDF_DIR.exists()}")
    
    # ===== ТРЕБОВАНИЕ 1: ПРОВЕРКА ТОКЕНА =====
    if not config.BOT_TOKEN:
        logger.critical("❌ TELEGRAM_TOKEN не найден!")
        print("ERROR: Set TELEGRAM_TOKEN in .env or hosting panel")
        sys.exit(1)
    
    # ===== СОЗДАНИЕ ПРИЛОЖЕНИЯ =====
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # ===== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ =====
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_error_handler(error_handler)
    
    # ===== ЗАПУСК =====
    logger.info("✅ Бот готов к работе")
    print("🚀 Tempo Bot запущен!")
    
    # ===== ТРЕБОВАНИЕ 1: ПРОВЕРКА __name__ =====
    if __name__ == "__main__":
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            timeout=30,
            drop_pending_updates=True,
        )


# ===== ЗАПУСК =====
# ===== ТРЕБОВАНИЕ 1: УСЛОВИЕ __name__ =====
if __name__ == "__main__":
    main()
