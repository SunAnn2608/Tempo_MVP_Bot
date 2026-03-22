"""
🎵 Tempo Bot — Telegram-бот для баланса работы и отдыха
Проект для итогового задания по Python

ТРЕБОВАНИЯ ПРОЕКТА:
✅ 1. Условия — if/else в анализе, обработчиках, AI
✅ 2. Словари — PRACTICES, user_data, настройки
✅ 3. Функции — 30+ функций для анализа, AI, файлов
✅ 4. Файлы — JSON, PDF, аудио, загрузка от пользователя
✅ 5. Оригинальность — AI-анализ + аудио-практики + готовые материалы

УТП: Помоги себе избежать выгорания всего за 5 минут в день
"""

import json
import os
import random
from datetime import datetime, time
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)

import config
from ai_analyzer import analyze_schedule_text, extract_tasks_from_text, get_quick_tip
from file_parser import parse_file, validate_file
from task_manager import (
    get_user_data, get_user_tasks, add_task, get_task,
    edit_task, delete_task, get_tasks_summary, mark_task_completed, clear_all_tasks
)
from reminders import get_random_reminder, get_reminder_by_time

# ===== ЗАГРУЗКА/СОХРАНЕНИЕ ДАННЫХ =====

def load_data(filename='data.json'):
    """Чтение данных из файла (ТРЕБОВАНИЕ 4)"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'users': {}}


def save_data(data, filename='data.json'):
    """Сохранение данных в файл (ТРЕБОВАНИЕ 4)"""
    Path('stats').mkdir(exist_ok=True)
    Path(config.UPLOADS_DIR).mkdir(exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===== КЛАВИАТУРЫ =====

def get_main_keyboard():
    """Главное меню Tempo"""
    return ReplyKeyboardMarkup([
        ['📋 Мои задачи'],
        ['🎧 5 минут для себя'],
        ['📥 Материалы и шаблоны'],
        ['⚙️ Настройки', '❓ Помощь']
    ], resize_keyboard=True)


def get_planning_mode_keyboard():
    """Выбор режима планирования"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 На день", callback_data="plan_daily")],
        [InlineKeyboardButton("📆 На неделю", callback_data="plan_weekly")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])


def get_upload_format_keyboard():
    """Выбор формата загрузки"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Текстом", callback_data="upload_text")],
        [InlineKeyboardButton("📄 TXT файл", callback_data="upload_txt")],
        [InlineKeyboardButton("📊 CSV файл", callback_data="upload_csv")],
        [InlineKeyboardButton("📈 Excel файл", callback_data="upload_excel")],
        [InlineKeyboardButton("📕 PDF (текст)", callback_data="upload_pdf")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])


def get_practices_keyboard():
    """Клавиатура с 5 аудио-практиками"""
    keyboard = []
    for key, practice in config.PRACTICES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{practice['icon']} {practice['name']} ⏱️{practice['duration']}",
                callback_data=f"practice_{key}"
            )
        ])
    keyboard.append([InlineKeyboardButton(f"💡 {config.USP_SHORT}", callback_data="usp_info")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def get_resources_keyboard():
    """Клавиатура ресурсов"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Трекер привычек", callback_data="res_tracker")],
        [InlineKeyboardButton("📖 Методичка по балансу", callback_data="res_methodology")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])


def get_tasks_list_keyboard(tasks: dict, planning_mode: str) -> InlineKeyboardMarkup:
    """Клавиатура со списком задач"""
    keyboard = []
    days_ru = {'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср', 'Thursday': 'Чт', 'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'}
    
    for day in config.DAYS_EN:
        day_tasks = [t for t in tasks.values() if t.get('day') == day]
        if day_tasks:
            keyboard.append([InlineKeyboardButton(f"📅 {days_ru.get(day, day)} ({len(day_tasks)})", callback_data=f"day_{day}")])
            for task in day_tasks:
                status = '✅' if task.get('completed') else '⏳'
                keyboard.append([InlineKeyboardButton(f"{status} #{task['id']} {task['title'][:20]}", callback_data=f"task_{task['id']}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить задачу", callback_data="add_new_task")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def get_task_actions_keyboard(task_id: int, planning_mode: str) -> InlineKeyboardMarkup:
    """Клавиатура действий для задачи"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{task_id}")],
        [InlineKeyboardButton("📅 Перенести день", callback_data=f"move_{task_id}")],
        [InlineKeyboardButton("⏱️ Изменить время", callback_data=f"duration_{task_id}")],
        [InlineKeyboardButton("✅ Выполнено", callback_data=f"complete_{task_id}")],
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{task_id}")],
        [InlineKeyboardButton("🔙 К списку", callback_data="tasks_list")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="back_main")]
    ])


# ===== ОБРАБОТЧИКИ КОМАНД =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_id = user.id
    get_user_data(user_id)
    
    welcome_card = os.path.join(config.IMAGES_DIR, 'brand', 'welcome_card.png')
    
    if os.path.exists(welcome_card):
        await update.message.reply_photo(
            photo=open(welcome_card, 'rb'),
            caption=(
                f"👋 Привет, {user.first_name}!\n\n"
                f"🎵 Я — {config.BOT_NAME}\n"
                f"✨ {config.USP_FULL}\n\n"
                "Выберите действие:",
            ),
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"🎵 Я — {config.BOT_NAME}\n"
            f"✨ {config.USP_FULL}\n\n"
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline-кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    planning_mode = context.user_data.get('planning_mode', 'weekly')
    
    if data == "back_main":
        await query.edit_message_text("Выберите действие:", reply_markup=get_main_keyboard())
    
    elif data == "tasks_list":
        tasks = get_user_tasks(user_id, planning_mode)
        summary = get_tasks_summary(user_id, planning_mode)
        await query.edit_message_text(summary, reply_markup=get_tasks_list_keyboard(tasks, planning_mode))
    
    elif data.startswith("task_"):
        task_id = int(data.split("_")[1])
        task = get_task(user_id, task_id, planning_mode)
        
        if task is None:
            await query.edit_message_text("❌ Задача не найдена")
            return
        
        priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task.get('priority'), '⚪')
        status = '✅ Выполнена' if task.get('completed') else '⏳ В процессе'
        days_ru = {'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда', 'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота', 'Sunday': 'Воскресенье'}
        
        description = (
            f"📋 *Задача #{task['id']}*\n\n"
            f"📝 *Название:* {task['title']}\n"
            f"📅 *День:* {days_ru.get(task['day'], task['day'])}\n"
            f"⏱️ *Длительность:* {task['duration_hours']} ч\n"
            f"🎯 *Приоритет:* {priority_icon}\n"
            f"📊 *Статус:* {status}\n\n"
            f"✨ {config.USP_SHORT}"
        )
        
        await query.edit_message_text(description, parse_mode='Markdown', reply_markup=get_task_actions_keyboard(task_id, planning_mode))
    
    elif data.startswith("practice_"):
        practice_key = data.split("_", 1)[1]
        practice = config.PRACTICES.get(practice_key)
        
        if practice is None:
            await query.edit_message_text("❌ Практика не найдена")
            return
        
        audio_path = os.path.join(config.AUDIO_DIR, practice['audio_file'])
        
        await query.edit_message_text(
            f"{practice['icon']} *{practice['name']}*\n\n"
            f"⏱️ {practice['duration']}\n"
            f"{practice['description']}",
            parse_mode='Markdown'
        )
        
        if os.path.exists(audio_path):
            await context.bot.send_audio(
                chat_id=user_id,
                audio=open(audio_path, 'rb'),
                caption=f"🎧 {practice['name']}\n\n💚 {practice['benefit']}\n\n✨ {config.USP_SHORT}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Прослушал", callback_data=f"tried_{practice_key}")],
                    [InlineKeyboardButton("🔙 Все практики", callback_data="practices_list")]
                ])
            )
            
            data_store = load_data()
            data_store['users'][str(user_id)]['stats']['practices_used'] = \
                data_store['users'][str(user_id)]['stats'].get('practices_used', 0) + 1
            save_data(data_store)
    
    elif data == "practices_list":
        practices_text = f"🎧 *5 минут для себя*\n\n✨ {config.USP_FULL}\n\nВыберите практику:\n"
        for key, practice in config.PRACTICES.items():
            practices_text += f"\n{practice['icon']} {practice['name']} ({practice['duration']})"
        await query.edit_message_text(practices_text, parse_mode='Markdown', reply_markup=get_practices_keyboard())
    
    elif data.startswith("tried_"):
        await query.edit_message_text(
            f"👏 Практика завершена!\n\n✨ {config.USP_SHORT}\n\n💚 Ты инвестировал 5 минут в своё здоровье!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎧 Ещё практика", callback_data="practices_list")],
                [InlineKeyboardButton("🏠 В главное меню", callback_data="back_main")]
            ])
        )
    
    elif data == "res_tracker":
        filepath = os.path.join(config.PDF_DIR, 'tracker_template.pdf')
        if os.path.exists(filepath):
            await query.edit_message_text("📋 Отправляю трекер...")
            await context.bot.send_document(
                chat_id=user_id,
                document=open(filepath, 'rb'),
                caption=f"📋 Трекер привычек\n\n✨ {config.USP_SHORT}"
            )
            await query.edit_message_text("✅ Трекер отправлен!")
        else:
            await query.edit_message_text("⚠️ Файл недоступен")
    
    elif data == "res_methodology":
        filepath = os.path.join(config.PDF_DIR, 'methodology_guide.pdf')
        if os.path.exists(filepath):
            await query.edit_message_text("📖 Отправляю методичку...")
            await context.bot.send_document(
                chat_id=user_id,
                document=open(filepath, 'rb'),
                caption=f"📖 Методичка по балансу\n\n✨ {config.USP_SHORT}"
            )
            await query.edit_message_text("✅ Методичка отправлена!")
        else:
            await query.edit_message_text("⚠️ Файл недоступен")
    
    elif data.startswith("plan_"):
        planning_mode = data.split("_")[1]
        context.user_data['planning_mode'] = planning_mode
        await query.edit_message_text(
            f"📋 Режим: {'день' if planning_mode == 'daily' else 'неделя'}\n\nВыберите формат:",
            reply_markup=get_upload_format_keyboard()
        )
    
    elif data.startswith("edit_"):
        task_id = int(data.split("_")[1])
        context.user_data['editing_task_id'] = task_id
        await query.edit_message_text(
            "✏️ *Редактирование*\n\nОтправьте: `номер новое_значение`\n\n1️⃣ Название\n2️⃣ День\n3️⃣ Длительность\n4️⃣ Приоритет",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")]
            ])
        )
    
    elif data.startswith("delete_"):
        task_id = int(data.split("_")[1])
        await query.edit_message_text(
            f"🗑️ *Удалить задачу #{task_id}?*\n\nЭто нельзя отменить.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да", callback_data=f"delete_confirm_{task_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data=f"task_{task_id}")]
            ])
        )
    
    elif data.startswith("delete_confirm_"):
        task_id = int(data.split("_")[2])
        result = delete_task(user_id, task_id, planning_mode)
        if result['success']:
            await query.edit_message_text(f"{result['message']}\n\n✨ {config.USP_SHORT}")
        else:
            await query.edit_message_text(f"❌ {result['error']}")
    
    elif data.startswith("complete_"):
        task_id = int(data.split("_")[1])
        result = mark_task_completed(user_id, task_id, planning_mode)
        if result['success']:
            await query.edit_message_text(f"✅ Задача #{task_id} выполнена!\n\n✨ {config.USP_SHORT}")
        else:
            await query.edit_message_text(f"❌ {result['error']}")
    
    elif data.startswith("move_"):
        task_id = int(data.split("_")[1])
        days_ru = {'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср', 'Thursday': 'Чт', 'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'}
        keyboard = [[InlineKeyboardButton(days_ru.get(d, d), callback_data=f"moveto_{d}_{task_id}")] for d in config.DAYS_EN]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")])
        await query.edit_message_text("📅 Выберите день:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("moveto_"):
        parts = data.split("_")
        new_day = parts[1]
        task_id = int(parts[2])
        result = edit_task(user_id, task_id, {'day': new_day}, planning_mode)
        if result['success']:
            await query.edit_message_text(f"✅ Задача перенесена на {new_day}\n\n✨ {config.USP_SHORT}")
        else:
            await query.edit_message_text(f"❌ {result['error']}")
    
    elif data.startswith("duration_"):
        task_id = int(data.split("_")[1])
        context.user_data['changing_duration_task_id'] = task_id
        await query.edit_message_text("⏱️ Отправьте новую длительность в часах (число):")
    
    elif data == "add_new_task":
        await query.edit_message_text(
            "➕ *Новая задача*\n\nФормат: `Название | День | Часы | Приоритет`\n\nПример: `Встреча | Monday | 2 | high`",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for_new_task'] = True
    
    elif data == "usp_info":
        await query.edit_message_text(
            f"💡 *Почему 5 минут?*\n\n🧠 Короткие регулярные практики эффективнее редких долгих.\n\n✨ {config.USP_FULL}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎧 Практики", callback_data="practices_list")],
                [InlineKeyboardButton("🏠 Меню", callback_data="back_main")]
            ])
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    planning_mode = context.user_data.get('planning_mode', 'weekly')
    
    if context.user_data.get('waiting_for_new_task', False):
        parts = text.split('|')
        if len(parts) >= 4:
            task_data = {'title': parts[0].strip(), 'day': parts[1].strip(), 'duration_hours': float(parts[2].strip()), 'priority': parts[3].strip().lower()}
        else:
            task_data = {'title': text.strip(), 'day': 'Monday', 'duration_hours': 1, 'priority': 'medium'}
        
        result = add_task(user_id, task_data, planning_mode)
        if result['success']:
            await update.message.reply_text(f"{result['message']}\n\n✨ {config.USP_SHORT}", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(f"❌ {result['error']}")
        context.user_data['waiting_for_new_task'] = None
        return
    
    if context.user_data.get('editing_task_id') is not None:
        task_id = context.user_data['editing_task_id']
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2:
            await update.message.reply_text("❌ Формат: `номер значение`")
            return
        
        field_num = parts[0]
        new_value = parts[1]
        updates = {}
        
        if field_num == '1':
            updates['title'] = new_value
        elif field_num == '2':
            updates['day'] = new_value
        elif field_num == '3':
            try:
                updates['duration_hours'] = float(new_value)
            except ValueError:
                await update.message.reply_text("❌ Длительность должна быть числом")
                return
        elif field_num == '4':
            if new_value.lower() in ['low', 'medium', 'high']:
                updates['priority'] = new_value.lower()
            else:
                await update.message.reply_text("❌ Приоритет: low, medium, high")
                return
        
        result = edit_task(user_id, task_id, updates, planning_mode)
        if result['success']:
            await update.message.reply_text(f"✅ {result['message']}\n\n✨ {config.USP_SHORT}", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(f"❌ {result['error']}")
        
        context.user_data['editing_task_id'] = None
        return
    
    if context.user_data.get('changing_duration_task_id') is not None:
        task_id = context.user_data['changing_duration_task_id']
        try:
            new_duration = float(text)
            result = edit_task(user_id, task_id, {'duration_hours': new_duration}, planning_mode)
            if result['success']:
                await update.message.reply_text(f"✅ Длительность: {new_duration} ч\n\n✨ {config.USP_SHORT}", reply_markup=get_main_keyboard())
            else:
                await update.message.reply_text(f"❌ {result['error']}")
        except ValueError:
            await update.message.reply_text("❌ Отправьте число")
        context.user_data['changing_duration_task_id'] = None
        return
    
    if text == '📋 Мои задачи':
        tasks = get_user_tasks(user_id, planning_mode)
        summary = get_tasks_summary(user_id, planning_mode)
        await update.message.reply_text(summary, reply_markup=get_tasks_list_keyboard(tasks, planning_mode))
    
    elif text == '🎧 5 минут для себя':
        practices_text = f"🎧 *5 минут для себя*\n\n✨ {config.USP_FULL}\n\nВыберите практику:"
        await update.message.reply_text(practices_text, parse_mode='Markdown', reply_markup=get_practices_keyboard())
    
    elif text == '📥 Материалы и шаблоны':
        await update.message.reply_text("📥 Выберите материал:", reply_markup=get_resources_keyboard())
    
    elif text == '⚙️ Настройки':
        user_data = get_user_data(user_id)
        stats = user_data.get('stats', {})
        await update.message.reply_text(
            f"⚙️ Статистика:\n\n"
            f"📋 Задач добавлено: {stats.get('tasks_added', 0)}\n"
            f"✅ Выполнено: {stats.get('tasks_completed', 0)}\n"
            f"✏️ Редактировано: {stats.get('tasks_edited', 0)}\n"
            f"🎧 Практик: {stats.get('practices_used', 0)}\n\n"
            f"✨ {config.USP_SHORT}"
        )
    
    elif text == '❓ Помощь':
        await update.message.reply_text(
            f"💡 {config.BOT_NAME} — Помощь:\n\n"
            "📋 Задачи: просмотр, редактирование, удаление\n"
            "🎧 Практики: 5 аудио по 5 минут\n"
            "📥 Материалы: трекер + методичка PDF\n\n"
            f"✨ {config.USP_SHORT}"
        )
    
    else:
        await update.message.reply_text(f"Используйте кнопки меню.\n\n✨ {config.USP_SHORT}", reply_markup=get_main_keyboard())


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка файлов от пользователя"""
    user_id = update.effective_user.id
    planning_mode = context.user_data.get('planning_mode', 'weekly')
    
    await update.message.reply_text("🤖 Получил файл! Анализирую...")
    
    if update.message.document:
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name
        ext = os.path.splitext(file_name)[1].lower()
        
        allowed = ['.txt', '.csv', '.xlsx', '.xls', '.pdf']
        if ext not in allowed:
            await update.message.reply_text(f"❌ Неподдерживаемый формат: {ext}")
            return
        
        Path(config.UPLOADS_DIR).mkdir(exist_ok=True)
        file_path = os.path.join(config.UPLOADS_DIR, f"user_{user_id}_{file_name}")
        await file.download_to_drive(file_path)
        
        validation = validate_file(file_path)
        if not validation['valid']:
            await update.message.reply_text(f"❌ {validation['error']}")
            return
        
        content = parse_file(file_path, validation['type'])
        
        if content.startswith("Ошибка") or content.startswith("⚠️"):
            await update.message.reply_text(f"❌ {content}")
            return
        
        await update.message.reply_text("🤖 AI анализирует...")
        analysis = analyze_schedule_text(content, planning_mode)
        tasks = extract_tasks_from_text(content, planning_mode)
        
        risk_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'}.get(analysis.get('risk_level'), '⚪')
        report = f"📊 AI-Анализ\n\nРиск: {risk_emoji} {analysis.get('risk_level', 'unknown').upper()}\n"
        
        if analysis.get('warnings'):
            report += "\n⚠️ " + "\n".join(analysis['warnings'][:3])
        if analysis.get('recommendations'):
            report += "\n\n💡 " + "\n".join(analysis['recommendations'][:3])
        
        report += f"\n\n✨ {config.USP_SHORT}"
        await update.message.reply_text(report)
        
        if tasks:
            for task in tasks:
                add_task(user_id, task, planning_mode)
            await update.message.reply_text(f"✅ Добавлено {len(tasks)} задач!", reply_markup=get_main_keyboard())
        
        if os.path.exists(file_path):
            os.remove(file_path)
    
    elif update.message.photo:
        await update.message.reply_text("❌ Картинки не поддерживаются. Используйте TXT, CSV, Excel, PDF с текстом.")


async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневное напоминание"""
    job = context.job
    user_id = job.chat_id
    
    user_data = get_user_data(user_id)
    if not user_data['settings'].get('reminders_enabled', True):
        return
    
    reminder_text, category = get_reminder_by_time()
    icons = {'microbreak': '☕', 'stretch': '🧘‍♀️', 'fresh_air': '🌿', 'water': '💧', 'motivation': '✨'}
    icon = icons.get(category, '🔔')
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"{icon} {reminder_text}\n\n🎵 {config.USP_SHORT}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Сделал!", callback_data="reminder_done")]])
    )


async def reminder_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки напоминания"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"👏 Отлично! Заботьтесь о себе!\n\n✨ {config.USP_SHORT}")


# ===== ТОЧКА ВХОДА =====

def main():
    """Запуск бота"""
    if config.TELEGRAM_TOKEN == 'YOUR_TELEGRAM_TOKEN_HERE':
        print("❌ Вставьте TELEGRAM_TOKEN в .env файл!")
        return
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    
    # Напоминания
    application.job_queue.run_daily(send_daily_reminder, time=time(10, 0))
    application.job_queue.run_daily(send_daily_reminder, time=time(14, 0))
    application.job_queue.run_daily(send_daily_reminder, time=time(17, 0))
    application.add_handler(CallbackQueryHandler(reminder_done, pattern="^reminder_done$"))
    
    print(f"🎵 {config.BOT_NAME} v{config.BOT_VERSION} запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()