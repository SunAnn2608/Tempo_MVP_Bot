"""
💬 Tempo Bot — Обратная связь

Два канала сбора:
  1. Быстрый опрос после практики — оценка 1–5 звёзд
  2. Свободный текст через кнопку «Оставить отзыв»

Просмотр для админа: /feedback_admin
  — последние N отзывов с датой, пользователем, типом
"""

import logging
from datetime import datetime
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from task_manager import load_data, save_data

logger = logging.getLogger(__name__)

# ===== ХРАНИЛИЩЕ =====

def _save_feedback(user_id: int, fb_type: str, payload: dict):
    """Добавляет запись в data['feedback'] (глобальный список)."""
    data = load_data()
    if "feedback" not in data:
        data["feedback"] = []

    # Получаем имя пользователя если есть в users
    uid = str(user_id)
    user_info = data.get("users", {}).get(uid, {})

    record = {
        "id":         len(data["feedback"]) + 1,
        "user_id":    user_id,
        "username":   user_info.get("username", "—"),
        "first_name": user_info.get("first_name", "—"),
        "type":       fb_type,          # "practice_rating" | "free_text"
        "timestamp":  datetime.now().isoformat(),
        **payload,
    }
    data["feedback"].append(record)
    # Храним не более 500 записей
    if len(data["feedback"]) > 500:
        data["feedback"] = data["feedback"][-500:]
    save_data(data)
    logger.info(f"Обратная связь сохранена: user={user_id}, type={fb_type}")


def save_user_meta(user_id: int, username: Optional[str], first_name: Optional[str]):
    """Обновляет мета-данные пользователя (имя/ник) при первом контакте."""
    data = load_data()
    uid = str(user_id)
    user = data.setdefault("users", {}).setdefault(uid, {})
    user["username"]   = username or "—"
    user["first_name"] = first_name or "—"
    save_data(data)


# ===== ОПРОС ПОСЛЕ ПРАКТИКИ =====

def practice_rating_keyboard(practice_key: str) -> InlineKeyboardMarkup:
    stars = [
        InlineKeyboardButton(
            "⭐" * i,
            callback_data=f"fb_rate_{practice_key}_{i}"
        )
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup([
        stars[:3],
        stars[3:],
        [InlineKeyboardButton("Пропустить", callback_data="fb_skip")],
    ])


async def ask_practice_rating(bot, user_id: int, practice_key: str, practice_name: str):
    """Отправляет запрос оценки после завершения практики."""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎧 Практика <b>{practice_name}</b> завершена!\n\nКак ощущения? Оцени:",
            parse_mode="HTML",
            reply_markup=practice_rating_keyboard(practice_key),
        )
    except Exception as e:
        logger.error(f"Ошибка запроса оценки практики: {e}")


# ===== СВОБОДНЫЙ ОТЗЫВ =====

async def start_free_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает сценарий свободного отзыва."""
    context.user_data["step"] = "feedback_text"
    await update.message.reply_text(
        "💬 <b>Оставить отзыв</b>\n\n"
        "Напиши, что думаешь о боте: что нравится, что мешает, "
        "чего не хватает — любой текст.\n\n"
        "Мы читаем каждый отзыв 🙏",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data="fb_cancel")]
        ]),
    )


# ===== ОБРАБОТЧИК CALLBACKS =====

async def handle_feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Обрабатывает fb_* callbacks. Возвращает True если обработал."""
    query = update.callback_query
    data  = query.data
    if not data.startswith("fb_"):
        return False

    await query.answer()
    user_id = query.from_user.id

    # Пропустить оценку
    if data == "fb_skip":
        await query.edit_message_text("👌 Хорошо, в следующий раз!")
        return True

    # Отмена свободного отзыва
    if data == "fb_cancel":
        context.user_data.pop("step", None)
        await query.edit_message_text("❌ Отменено")
        return True

    # Оценка практики: fb_rate_<key>_<stars>
    if data.startswith("fb_rate_"):
        parts = data.split("_")          # ['fb','rate','p1','3']
        if len(parts) == 4:
            practice_key = parts[2]
            stars        = int(parts[3])
            practice_name = config.PRACTICES.get(
                "p" + practice_key[1:] if not practice_key.startswith("p") else practice_key,
                {}
            ).get("name", practice_key)

            _save_feedback(user_id, "practice_rating", {
                "practice_key":  practice_key,
                "practice_name": practice_name,
                "stars":         stars,
            })

            star_str = "⭐" * stars
            comment  = {5: "Отлично!", 4: "Хорошо!", 3: "Нормально", 2: "Надо улучшить", 1: "Не понравилось"}.get(stars, "")
            await query.edit_message_text(
                f"{star_str} {comment}\n\nСпасибо за оценку — это помогает нам развиваться 🙏"
            )
        return True

    return False


async def handle_feedback_text(user_id: int, text: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Вызывается из handle_text когда step == 'feedback_text'."""
    if context.user_data.get("step") != "feedback_text":
        return False

    if len(text.strip()) < 3:
        return True  # слишком короткий — игнорируем, не сбрасываем шаг

    _save_feedback(user_id, "free_text", {"text": text.strip()})
    context.user_data.pop("step", None)
    return True   # сигнал для bot.py что текст обработан


# ===== ПРОСМОТР ДЛЯ АДМИНА =====

def format_feedback_for_admin(limit: int = 20) -> str:
    """Форматирует последние `limit` отзывов для вывода админу."""
    data     = load_data()
    feedbacks = data.get("feedback", [])

    if not feedbacks:
        return "📭 Отзывов пока нет."

    recent = list(reversed(feedbacks[-limit:]))
    lines  = [f"📬 <b>Последние отзывы ({len(feedbacks)} всего):</b>\n"]

    for fb in recent:
        dt       = datetime.fromisoformat(fb["timestamp"]).strftime("%d.%m %H:%M")
        name     = fb.get("first_name", "—")
        username = fb.get("username", "")
        user_str = f"@{username}" if username and username != "—" else f"id{fb['user_id']}"

        if fb["type"] == "practice_rating":
            stars   = "⭐" * fb.get("stars", 0)
            pr_name = fb.get("practice_name", fb.get("practice_key", "—"))
            lines.append(f"🎧 <b>{dt}</b> {name} ({user_str})\n   {pr_name} → {stars}\n")

        elif fb["type"] == "free_text":
            txt = fb.get("text", "")[:200]
            lines.append(f"💬 <b>{dt}</b> {name} ({user_str})\n   {txt}\n")

    return "\n".join(lines)


def get_feedback_stats() -> str:
    data      = load_data()
    feedbacks = data.get("feedback", [])

    if not feedbacks:
        return "📭 Отзывов нет."

    ratings   = [f for f in feedbacks if f["type"] == "practice_rating"]
    texts     = [f for f in feedbacks if f["type"] == "free_text"]
    avg_stars = (
        round(sum(f["stars"] for f in ratings) / len(ratings), 1)
        if ratings else 0
    )

    # Топ практик по средней оценке
    from collections import defaultdict
    practice_scores: dict = defaultdict(list)
    for f in ratings:
        practice_scores[f.get("practice_name", "—")].append(f["stars"])
    top = sorted(
        [(name, round(sum(s)/len(s), 1), len(s)) for name, s in practice_scores.items()],
        key=lambda x: -x[1],
    )

    lines = [
        "📊 <b>Статистика обратной связи:</b>\n",
        f"💬 Свободных отзывов: {len(texts)}",
        f"⭐ Оценок практик: {len(ratings)}",
        f"📈 Средняя оценка: {avg_stars}/5\n",
        "<b>Практики по оценкам:</b>",
    ]
    for name, avg, cnt in top:
        lines.append(f"  {'⭐' * round(avg)} {name}  ({avg}/5, {cnt} оц.)")

    return "\n".join(lines)
