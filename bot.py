"""
🎵 Tempo Bot — Telegram-бот для баланса работы и отдыха
MVP версия (обновлённый: отметка/редактирование задач + обратная связь)
"""

import logging
import os
import sys

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
from task_manager import (
    add_task, get_tasks_summary, clear_all_tasks, get_task_statistics,
    delete_task, toggle_task_done, edit_task_field, load_data,
    PRIORITY_ICON, PRIORITY_LABEL,
)
from reminders import (
    send_reminder, setup_daily_reminders,
    handle_reminder_callback, toggle_reminders,
)
from ai_analyzer import analyze_schedule, format_analysis_result, save_analysis_history
from checkin import start_checkin, handle_checkin_callback
from feedback import (
    handle_feedback_callback, handle_feedback_text,
    start_free_feedback, ask_practice_rating,
    format_feedback_for_admin, get_feedback_stats,
    save_user_meta,
)

# ===== ЛОГИРОВАНИЕ =====

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8", mode="a"),
    ],
)
logger = logging.getLogger(__name__)

# ===== КОНСТАНТЫ =====

DAYS_RU = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
]

PRIORITY_LABELS = {
    "high":   "🔴 Высокий",
    "medium": "🟡 Средний",
    "low":    "🟢 Низкий",
}

# ID администратора — подставь свой Telegram user_id
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


# ===== КЛАВИАТУРЫ =====

def main_keyboard():
    return ReplyKeyboardMarkup(
        [["📋 Задачи", "🧘 Состояние"],
         ["🎧 Практики", "📥 Материалы"],
         ["💬 Оставить отзыв"]],
        resize_keyboard=True,
    )


def tasks_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить",    callback_data="task_add")],
        [InlineKeyboardButton("📄 Список",      callback_data="task_list")],
        [InlineKeyboardButton("✅ Выполнить",   callback_data="task_done_ask")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="task_edit_ask")],
        [InlineKeyboardButton("🗑 Удалить",     callback_data="task_delete_ask")],
        [InlineKeyboardButton("🧹 Очистить",   callback_data="task_clear")],
        [InlineKeyboardButton("📊 Статистика", callback_data="task_stats")],
        [InlineKeyboardButton("🤖 AI-анализ",  callback_data="ai_start")],
        [InlineKeyboardButton("🔙 Назад",      callback_data="back")],
    ])


def priority_keyboard(prefix: str = "task_p") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"{prefix}_{key}")]
        for key, label in PRIORITY_LABELS.items()
    ] + [[InlineKeyboardButton("❌ Отмена", callback_data="task_cancel")]])


def hours_keyboard(prefix: str = "task_h") -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(str(h), callback_data=f"{prefix}_{h}") for h in range(1, 6)]
    row2 = [InlineKeyboardButton(str(h), callback_data=f"{prefix}_{h}") for h in range(6, 11)]
    return InlineKeyboardMarkup([row1, row2,
        [InlineKeyboardButton("❌ Отмена", callback_data="task_cancel")]])


def days_keyboard(prefix: str = "task_d") -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(DAYS_RU), 3):
        rows.append([
            InlineKeyboardButton(d, callback_data=f"{prefix}_{d}")
            for d in DAYS_RU[i:i+3]
        ])
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="task_cancel")])
    return InlineKeyboardMarkup(rows)


def practices_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(p["name"], callback_data=f"p_{k}")]
        for k, p in config.PRACTICES.items()
    ])


def _task_pick_keyboard(tasks: list, cb_prefix: str) -> InlineKeyboardMarkup:
    """Универсальный список задач для выбора (done/edit/delete)."""
    buttons = []
    for i, t in enumerate(tasks):
        done_mark = "✅ " if t.get("done") else ""
        label = f"{i+1}. {done_mark}{t['title'][:28]}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"{cb_prefix}_{i}")])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="task_cancel")])
    return InlineKeyboardMarkup(buttons)


def edit_field_keyboard(task_idx: int) -> InlineKeyboardMarkup:
    """Выбор поля для редактирования."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Приоритет",   callback_data=f"tedit_field_{task_idx}_priority")],
        [InlineKeyboardButton("⏱️ Длительность", callback_data=f"tedit_field_{task_idx}_hours")],
        [InlineKeyboardButton("📅 День",         callback_data=f"tedit_field_{task_idx}_day")],
        [InlineKeyboardButton("❌ Отмена",       callback_data="task_cancel")],
    ])


# ===== ВСПОМОГАТЕЛЬНЫЕ =====

async def send_file(bot, chat_id, path, file_type):
    if not os.path.exists(path):
        await bot.send_message(chat_id, "⚠️ Файл временно недоступен")
        return False
    try:
        with open(path, "rb") as f:
            if file_type == "audio":   await bot.send_audio(chat_id, f)
            elif file_type == "photo": await bot.send_photo(chat_id, f)
            else:                      await bot.send_document(chat_id, f)
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки файла {path}: {e}")
        await bot.send_message(chat_id, "⚠️ Ошибка отправки файла")
        return False


def clear_task_state(context):
    for key in ["step", "task_draft", "edit_task_idx", "edit_field", "checkin"]:
        context.user_data.pop(key, None)


def _get_tasks_or_empty(user_id) -> list:
    data = load_data()
    return data.get("users", {}).get(str(user_id), {}).get("tasks", [])


# ===== /start =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_meta(user.id, user.username, user.first_name)
    logger.info(f"Start от {user.id} ({user.first_name})")
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"🎵 Я — Tempo Bot\n"
        f"{config.USP}\n\n"
        f"Выберите раздел:",
        reply_markup=main_keyboard(),
    )


# ===== ТЕКСТОВЫЕ КНОПКИ И ВВОД =====

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg     = update.message.text
    user_id = update.effective_user.id
    step    = context.user_data.get("step")

    logger.info(f"Текст от {user_id}: '{msg}' (step={step})")

    # ── Главное меню ──────────────────────────────────────────────
    if msg == "📋 Задачи":
        await update.message.reply_text("📋 Управление задачами:", reply_markup=tasks_keyboard())
        return
    if msg == "🎧 Практики":
        await update.message.reply_text("🎧 Выберите практику:", reply_markup=practices_keyboard())
        return
    if msg == "🧘 Состояние":
        await start_checkin(update, context)
        return
    if msg == "📥 Материалы":
        await _send_materials(update, context, user_id)
        return
    if msg == "💬 Оставить отзыв":
        await start_free_feedback(update, context)
        return

    # ── Свободный отзыв ───────────────────────────────────────────
    if step == "feedback_text":
        handled = await handle_feedback_text(user_id, msg, context)
        if handled:
            await update.message.reply_text(
                "💙 Спасибо! Твой отзыв получен — мы его обязательно прочитаем.",
                reply_markup=main_keyboard(),
            )
        return

    # ── Добавление задачи: шаг 1 (название) ──────────────────────
    if step == "task_title":
        title = msg.strip()
        if len(title) < 2:
            await update.message.reply_text("❌ Название слишком короткое, попробуй ещё раз:")
            return
        context.user_data["task_draft"] = {"title": title}
        context.user_data["step"] = "task_priority"
        await update.message.reply_text(
            f"✅ Название: <b>{title}</b>\n\n"
            f"🎯 <b>Шаг 2 из 4</b> — Выбери приоритет:",
            parse_mode="HTML",
            reply_markup=priority_keyboard(),
        )
        return

    # ── AI-анализ ─────────────────────────────────────────────────
    if step == "ai_input":
        if len(msg.strip()) < 20:
            await update.message.reply_text("❌ Слишком мало данных. Опишите расписание подробнее.")
            return
        await update.message.reply_text("🤖 Анализирую...")
        try:
            result    = analyze_schedule(msg)
            formatted = format_analysis_result(result)
            await update.message.reply_text(formatted, parse_mode="HTML")
            save_analysis_history(user_id, msg, result)
        except Exception as e:
            logger.error(f"Ошибка AI-анализа: {e}", exc_info=True)
            await update.message.reply_text("❌ Ошибка при анализе. Попробуйте ещё раз.")
        context.user_data.clear()
        return

    # ── Напоминания ───────────────────────────────────────────────
    if msg.lower() in ["напоминания вкл", "/reminders_on"]:
        toggle_reminders(user_id, True)
        await update.message.reply_text("🔔 Напоминания включены!")
        return
    if msg.lower() in ["напоминания выкл", "/reminders_off"]:
        toggle_reminders(user_id, False)
        await update.message.reply_text("🔕 Напоминания выключены")
        return

    await update.message.reply_text("💡 Используйте кнопки меню", reply_markup=main_keyboard())


async def _send_materials(update, context, user_id):
    guide_path   = config.PDF_DIR / "guide.pdf"
    tracker_path = config.PDF_DIR / "tracker.pdf"
    await update.message.reply_text("📥 Отправляю материалы...")
    sent = False
    for path in [guide_path, tracker_path]:
        if path.exists():
            await send_file(context.bot, user_id, path, "document")
            sent = True
    if not sent:
        await update.message.reply_text("⏳ Материалы в подготовке. Загляните позже!")


# ===== INLINE-CALLBACKS =====

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    data    = query.data
    user_id = query.from_user.id

    logger.info(f"Callback от {user_id}: {data}")

    # ── Обратная связь ────────────────────────────────────────────
    if await handle_feedback_callback(update, context):
        return

    # ── Чек-ин ────────────────────────────────────────────────────
    if await handle_checkin_callback(update, context):
        return

    if data == "checkin_start":
        context.user_data["checkin"] = {}
        context.user_data["step"] = "checkin"
        from checkin import CHECKIN_STEPS, scale_keyboard
        step_cfg = CHECKIN_STEPS[0]
        await query.edit_message_text(
            step_cfg["question"], parse_mode="HTML",
            reply_markup=scale_keyboard(step_cfg["key"]),
        )
        return

    # ── Практики ─────────────────────────────────────────────────
   if data.startswith("p_"):
    raw = data[2:]          # всё после "p_"
    key = raw if raw.startswith("p") else "p" + raw
        practice = config.PRACTICES.get(key)
        if not practice:
            await query.edit_message_text("❌ Практика не найдена")
            return
        await query.edit_message_text(
            f"🎧 <b>{practice['name']}</b>\n\n⏱️ 5 минут\n📝 {practice['desc']}",
            parse_mode="HTML",
        )
        await send_file(context.bot, user_id, config.IMAGES_DIR / practice["image"], "photo")
        await send_file(context.bot, user_id, config.AUDIO_DIR  / practice["audio"], "audio")
        # Запрашиваем оценку через 5 секунд (просто сразу для MVP)
        await ask_practice_rating(context.bot, user_id, key, practice["name"])
        return

    # ─────────────────────────────────────────────────────────────
    # ЗАДАЧИ
    # ─────────────────────────────────────────────────────────────

    if data == "task_add":
        clear_task_state(context)
        context.user_data["step"] = "task_title"
        await query.message.reply_text(
            "✏️ <b>Шаг 1 из 4</b> — Введи название задачи:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="task_cancel")]
            ]),
        )
        return

    if data == "task_list":
        text = get_tasks_summary(user_id)
        await query.message.reply_text(text, parse_mode="HTML")
        return

    if data == "task_clear":
        clear_all_tasks(user_id)
        await query.message.reply_text("🧹 Все задачи удалены")
        return

    if data == "task_stats":
        s = get_task_statistics(user_id)
        text = (
            f"📊 <b>Статистика задач:</b>\n\n"
            f"📋 Всего: {s['total']}\n"
            f"✅ Выполнено: {s['done']}\n"
            f"⏳ Осталось: {s['pending']}\n"
            f"⏱️ Часов всего: {s['total_hours']}  /  выполнено: {s['done_hours']}\n\n"
            f"🔴 Высокий приоритет: {s['by_priority']['high']}\n"
            f"🟡 Средний: {s['by_priority']['medium']}\n"
            f"🟢 Низкий: {s['by_priority']['low']}"
        )
        await query.message.reply_text(text, parse_mode="HTML")
        return

    # ── Отметить выполненной ─────────────────────────────────────
    if data == "task_done_ask":
        tasks = _get_tasks_or_empty(user_id)
        if not tasks:
            await query.message.reply_text("📭 Нет задач")
            return
        await query.message.reply_text(
            "✅ <b>Выбери задачу для отметки:</b>",
            parse_mode="HTML",
            reply_markup=_task_pick_keyboard(tasks, "task_done"),
        )
        return

    if data.startswith("task_done_"):
        idx     = int(data.split("_")[2])
        updated = toggle_task_done(user_id, idx)
        if updated:
            status = "✅ Выполнена" if updated.get("done") else "◻️ Возвращена в список"
            await query.message.reply_text(
                f"{status}: <b>{updated['title']}</b>",
                parse_mode="HTML",
            )
        else:
            await query.message.reply_text("❌ Задача не найдена")
        return

    # ── Редактировать задачу ─────────────────────────────────────
    if data == "task_edit_ask":
        tasks = _get_tasks_or_empty(user_id)
        if not tasks:
            await query.message.reply_text("📭 Нет задач для редактирования")
            return
        await query.message.reply_text(
            "✏️ <b>Выбери задачу для редактирования:</b>",
            parse_mode="HTML",
            reply_markup=_task_pick_keyboard(tasks, "task_edit_pick"),
        )
        return

    if data.startswith("task_edit_pick_"):
        idx = int(data.split("_")[3])
        tasks = _get_tasks_or_empty(user_id)
        if not (0 <= idx < len(tasks)):
            await query.message.reply_text("❌ Задача не найдена")
            return
        t = tasks[idx]
        context.user_data["edit_task_idx"] = idx
        p_label = PRIORITY_LABELS.get(t.get("priority", "medium"), "")
        await query.message.reply_text(
            f"✏️ <b>Редактировать:</b> {t['title']}\n"
            f"Приоритет: {p_label}  |  {t.get('duration_hours',1)}ч  |  {t.get('day','—')}\n\n"
            f"Что изменить?",
            parse_mode="HTML",
            reply_markup=edit_field_keyboard(idx),
        )
        return

    # Выбор поля: tedit_field_<idx>_<field>
    if data.startswith("tedit_field_"):
        parts = data.split("_")          # ['tedit','field','2','priority']
        idx   = int(parts[2])
        field = parts[3]
        context.user_data["edit_task_idx"] = idx
        context.user_data["edit_field"]    = field

        if field == "priority":
            await query.edit_message_text(
                "🎯 Выбери новый приоритет:",
                reply_markup=priority_keyboard("tedit_p"),
            )
        elif field == "hours":
            await query.edit_message_text(
                "⏱️ Выбери новую длительность:",
                reply_markup=hours_keyboard("tedit_h"),
            )
        elif field == "day":
            await query.edit_message_text(
                "📅 Выбери новый день:",
                reply_markup=days_keyboard("tedit_d"),
            )
        return

    # Применение нового значения поля
    if data.startswith("tedit_p_"):
        new_val = data.split("_")[2]
        idx     = context.user_data.get("edit_task_idx", -1)
        edit_task_field(user_id, idx, "priority", new_val)
        clear_task_state(context)
        await query.edit_message_text(
            f"✅ Приоритет обновлён: {PRIORITY_LABELS.get(new_val, new_val)}"
        )
        return

    if data.startswith("tedit_h_"):
        new_val = int(data.split("_")[2])
        idx     = context.user_data.get("edit_task_idx", -1)
        edit_task_field(user_id, idx, "duration_hours", new_val)
        clear_task_state(context)
        await query.edit_message_text(f"✅ Длительность обновлена: {new_val} ч")
        return

    if data.startswith("tedit_d_"):
        new_val = data[len("tedit_d_"):]
        idx     = context.user_data.get("edit_task_idx", -1)
        edit_task_field(user_id, idx, "day", new_val)
        clear_task_state(context)
        await query.edit_message_text(f"✅ День обновлён: {new_val}")
        return

    # ── Удаление ─────────────────────────────────────────────────
    if data == "task_delete_ask":
        tasks = _get_tasks_or_empty(user_id)
        if not tasks:
            await query.message.reply_text("📭 Нет задач для удаления")
            return
        await query.message.reply_text(
            "🗑 <b>Выбери задачу для удаления:</b>",
            parse_mode="HTML",
            reply_markup=_task_pick_keyboard(tasks, "task_del"),
        )
        return

    if data.startswith("task_del_"):
        idx     = int(data.split("_")[2])
        success = delete_task(user_id, idx)
        await query.message.reply_text(
            "✅ Задача удалена" if success else "❌ Задача не найдена"
        )
        return

    if data == "task_cancel":
        clear_task_state(context)
        await query.edit_message_text("❌ Отменено")
        return

    # ── Шаги добавления задачи (приоритет → часы → день) ─────────
    if data.startswith("task_p_"):
        priority = data.split("_")[2]
        draft    = context.user_data.get("task_draft", {})
        draft["priority"] = priority
        context.user_data["task_draft"] = draft
        context.user_data["step"] = "task_hours"
        await query.edit_message_text(
            f"✅ Приоритет: <b>{PRIORITY_LABELS.get(priority)}</b>\n\n"
            f"⏱️ <b>Шаг 3 из 4</b> — Сколько часов займёт задача?",
            parse_mode="HTML",
            reply_markup=hours_keyboard(),
        )
        return

    if data.startswith("task_h_"):
        hours = int(data.split("_")[2])
        draft = context.user_data.get("task_draft", {})
        draft["duration_hours"] = hours
        context.user_data["task_draft"] = draft
        context.user_data["step"] = "task_day"
        await query.edit_message_text(
            f"✅ Длительность: <b>{hours} ч</b>\n\n"
            f"📅 <b>Шаг 4 из 4</b> — На какой день запланировать?",
            parse_mode="HTML",
            reply_markup=days_keyboard(),
        )
        return

    if data.startswith("task_d_"):
        day   = data[len("task_d_"):]
        draft = context.user_data.get("task_draft", {})
        draft["day"] = day
        clear_task_state(context)
        try:
            add_task(user_id, draft)
            p_label = PRIORITY_LABELS.get(draft.get("priority", "medium"), "")
            await query.edit_message_text(
                f"✅ <b>Задача добавлена!</b>\n\n"
                f"📌 {draft['title']}\n"
                f"📅 {day}  ⏱️ {draft['duration_hours']}ч  {p_label}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Ещё задачу", callback_data="task_add")],
                    [InlineKeyboardButton("📄 Список",     callback_data="task_list")],
                    [InlineKeyboardButton("🏠 Меню",       callback_data="back")],
                ]),
            )
        except Exception as e:
            logger.error(f"Ошибка сохранения задачи: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Не удалось сохранить: {e}")
        return

    # ── AI-анализ ─────────────────────────────────────────────────
    if data == "ai_start":
        context.user_data["step"] = "ai_input"
        await query.message.reply_text(
            "🤖 <b>AI-анализ расписания</b>\n\n"
            "Отправьте расписание текстом.\n"
            "Пример: <i>Понедельник: Работа 8ч, Спорт 1ч</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="back")]
            ]),
        )
        return

    # ── Напоминания ───────────────────────────────────────────────
    if data in ("reminder_done", "practices_menu"):
        await handle_reminder_callback(update, context)
        return

    # ── Назад ────────────────────────────────────────────────────
    if data == "back":
        clear_task_state(context)
        await query.edit_message_text(
            "🏠 Главное меню",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Задачи",    callback_data="open_tasks")],
                [InlineKeyboardButton("🧘 Состояние", callback_data="checkin_start")],
                [InlineKeyboardButton("🎧 Практики",  callback_data="open_practices")],
            ]),
        )
        return

    if data == "open_tasks":
        await query.edit_message_text("📋 Управление задачами:", reply_markup=tasks_keyboard())
        return
    if data == "open_practices":
        await query.edit_message_text("🎧 Выберите практику:", reply_markup=practices_keyboard())
        return


# ===== КОМАНДЫ АДМИНИСТРАТОРА =====

async def cmd_feedback_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр последних отзывов (только для ADMIN_ID)."""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён")
        return

    limit = 20
    if context.args:
        try:
            limit = int(context.args[0])
        except ValueError:
            pass

    text = format_feedback_for_admin(limit)
    # Разбиваем на части если длинно
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await update.message.reply_text(chunk, parse_mode="HTML")


async def cmd_feedback_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика обратной связи (только для ADMIN_ID)."""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён")
        return
    await update.message.reply_text(get_feedback_stats(), parse_mode="HTML")


# ===== ОШИБКИ =====

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ Произошла ошибка. Попробуйте /start")


# ===== ТОЧКА ВХОДА =====

def main():
    logger.info("🎵 Tempo Bot запускается...")

    if not config.BOT_TOKEN:
        logger.critical("❌ TELEGRAM_TOKEN не найден!")
        sys.exit(1)

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",          start))
    app.add_handler(CommandHandler("feedback_admin", cmd_feedback_admin))
    app.add_handler(CommandHandler("feedback_stats", cmd_feedback_stats))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    try:
        setup_daily_reminders(app)
        logger.info("✅ Напоминания активированы")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось настроить напоминания: {e}")

    logger.info("✅ Бот готов к работе")
    print("🚀 Tempo Bot запущен!")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        timeout=30,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
