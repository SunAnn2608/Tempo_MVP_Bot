"""
🧘 Tempo Bot — Чек-ин состояния

Пошаговый тест по шкале 1–10:
  1. Энергия (1 = в ноль, 10 = заряжен)
  2. Стресс  (1 = спокойно, 10 = на пределе)
  3. Фокус   (1 = рассеян, 10 = в потоке)

По итогам — персональный результат + рекомендованная практика.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from task_manager import load_data, save_data

logger = logging.getLogger(__name__)

# ===== ШАГИ ЧЕКИНА =====

CHECKIN_STEPS = [
    {
        "key": "energy",
        "emoji": "⚡",
        "title": "Энергия",
        "question": "⚡ <b>Шаг 1 из 3 — Энергия</b>\n\nКак ты себя чувствуешь физически прямо сейчас?\n\n1 — совсем без сил\n10 — полон энергии",
    },
    {
        "key": "stress",
        "emoji": "🌊",
        "title": "Стресс",
        "question": "🌊 <b>Шаг 2 из 3 — Стресс</b>\n\nКакой у тебя уровень стресса или напряжения?\n\n1 — полностью спокоен\n10 — на пределе",
    },
    {
        "key": "focus",
        "emoji": "🎯",
        "title": "Фокус",
        "question": "🎯 <b>Шаг 3 из 3 — Фокус</b>\n\nНасколько легко тебе сейчас сосредоточиться?\n\n1 — мысли разбегаются\n10 — в потоке",
    },
]

# ===== КЛАВИАТУРА ОЦЕНКИ 1–10 =====

def scale_keyboard(step_key: str) -> InlineKeyboardMarkup:
    """Кнопки 1–10 в две строки: 1–5 и 6–10"""
    row1 = [InlineKeyboardButton(str(i), callback_data=f"ci_{step_key}_{i}") for i in range(1, 6)]
    row2 = [InlineKeyboardButton(str(i), callback_data=f"ci_{step_key}_{i}") for i in range(6, 11)]
    cancel = [InlineKeyboardButton("❌ Отмена", callback_data="ci_cancel")]
    return InlineKeyboardMarkup([row1, row2, cancel])


# ===== ЛОГИКА РЕЗУЛЬТАТА =====

def _score_bar(value: int, max_val: int = 10) -> str:
    """Мини-прогресс-бар из 10 символов"""
    filled = round(value * 10 / max_val)
    return "█" * filled + "░" * (10 - filled)


def interpret_results(energy: int, stress: int, focus: int) -> Dict:
    """
    Возвращает:
      - level:       'great' | 'ok' | 'tired' | 'critical'
      - title:       заголовок состояния
      - summary:     короткое описание
      - practice_key: ключ из config.PRACTICES для рекомендации
      - tips:        список советов
    """
    # Инвертируем стресс для общего балла (высокий стресс = плохо)
    stress_inv = 11 - stress
    total = energy + stress_inv + focus  # макс 30, мин 3

    if total >= 22:
        level = "great"
        title = "🟢 Отличное состояние"
        summary = "Ты в ресурсе — самое время для сложных задач!"
        practice_key = "p5"  # Глубокий фокус
        tips = [
            "Займись самой важной задачей прямо сейчас",
            "Это хорошее время для творческой работы",
            "Зафиксируй, что помогло тебе быть в таком состоянии",
        ]
    elif total >= 15:
        level = "ok"
        title = "🟡 Нормальное состояние"
        summary = "Всё в порядке, но есть куда расти."
        practice_key = "p1"  # Дыхание 4-7-8
        tips = [
            "Сделай короткий перерыв перед следующей задачей",
            "5 минут дыхательной практики подзарядят тебя",
            "Расставь приоритеты — не берись за всё сразу",
        ]
    elif total >= 9:
        level = "tired"
        title = "🟠 Устал — нужен отдых"
        summary = "Организм сигнализирует: пора сбавить темп."
        practice_key = "p4"  # Снять напряжение
        tips = [
            "Отложи несрочные задачи на завтра",
            "Сделай 15-минутный перерыв без экрана",
            "Попробуй практику расслабления прямо сейчас",
        ]
    else:
        level = "critical"
        title = "🔴 Критическое состояние"
        summary = "Ты на пределе. Сейчас важнее всего — восстановление."
        practice_key = "p3"  # Спокойный сон / вечерняя
        tips = [
            "Останови работу и дай себе отдохнуть",
            "Поговори с кем-то близким или просто побудь в тишине",
            "Практика сейчас важнее любой задачи",
        ]

    return {
        "level": level,
        "title": title,
        "summary": summary,
        "practice_key": practice_key,
        "tips": tips,
        "total": total,
        "energy": energy,
        "stress": stress,
        "focus": focus,
    }


def format_checkin_result(res: Dict) -> str:
    e, s, f = res["energy"], res["stress"], res["focus"]

    text = (
        f"{res['title']}\n\n"
        f"⚡ Энергия:  {_score_bar(e)} {e}/10\n"
        f"🌊 Стресс:   {_score_bar(s)} {s}/10\n"
        f"🎯 Фокус:    {_score_bar(f)} {f}/10\n\n"
        f"<i>{res['summary']}</i>\n\n"
        f"💡 <b>Советы:</b>\n"
    )
    for tip in res["tips"]:
        text += f"• {tip}\n"

    practice = config.PRACTICES.get(res["practice_key"])
    if practice:
        text += f"\n🎧 <b>Рекомендую практику:</b> {practice['name']}"

    return text


def result_keyboard(practice_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Открыть практику", callback_data=f"p_{practice_key[1:]}")],
        [InlineKeyboardButton("📊 История чек-инов", callback_data="ci_history")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back")],
    ])


# ===== СОХРАНЕНИЕ ИСТОРИИ =====

def save_checkin(user_id: int, result: Dict):
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {}
    if "checkins" not in data["users"][uid]:
        data["users"][uid]["checkins"] = []

    record = {
        "timestamp": datetime.now().isoformat(),
        "energy": result["energy"],
        "stress": result["stress"],
        "focus": result["focus"],
        "level": result["level"],
        "total": result["total"],
    }
    data["users"][uid]["checkins"].append(record)

    # Храним последние 30 записей
    if len(data["users"][uid]["checkins"]) > 30:
        data["users"][uid]["checkins"] = data["users"][uid]["checkins"][-30:]

    save_data(data)
    logger.info(f"Чек-ин сохранён для пользователя {user_id}: {result['level']}")


def get_checkin_history_text(user_id: int) -> str:
    data = load_data()
    uid = str(user_id)
    checkins = data.get("users", {}).get(uid, {}).get("checkins", [])

    if not checkins:
        return "📭 Чек-инов пока нет. Пройди первый!"

    text = "📊 <b>Последние чек-ины:</b>\n\n"
    level_icons = {"great": "🟢", "ok": "🟡", "tired": "🟠", "critical": "🔴"}

    for c in reversed(checkins[-7:]):  # последние 7
        dt = datetime.fromisoformat(c["timestamp"])
        date_str = dt.strftime("%d.%m %H:%M")
        icon = level_icons.get(c["level"], "⚪")
        text += (
            f"{icon} <b>{date_str}</b>  "
            f"⚡{c['energy']} 🌊{c['stress']} 🎯{c['focus']}\n"
        )

    return text


# ===== ХЭНДЛЕР ЧЕКИНА =====

async def start_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск чек-ина: первый вопрос"""
    context.user_data["checkin"] = {}
    context.user_data["step"] = "checkin"

    step = CHECKIN_STEPS[0]
    await update.message.reply_text(
        step["question"],
        parse_mode="HTML",
        reply_markup=scale_keyboard(step["key"]),
    )


async def handle_checkin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обрабатывает callback_data вида ci_<key>_<value> и служебные ci_cancel / ci_history.
    Возвращает True, если callback был обработан здесь.
    """
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if not data.startswith("ci_"):
        return False

    await query.answer()

    # --- Отмена ---
    if data == "ci_cancel":
        context.user_data.pop("checkin", None)
        context.user_data.pop("step", None)
        await query.edit_message_text("❌ Чек-ин отменён")
        return True

    # --- История ---
    if data == "ci_history":
        text = get_checkin_history_text(user_id)
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Новый чек-ин", callback_data="checkin_start")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back")],
            ]),
        )
        return True

    # --- Ответ на вопрос: ci_<key>_<value> ---
    parts = data.split("_")
    if len(parts) != 3:
        return False

    _, step_key, value_str = parts
    try:
        value = int(value_str)
    except ValueError:
        return False

    checkin = context.user_data.get("checkin", {})
    checkin[step_key] = value
    context.user_data["checkin"] = checkin

    # Определяем следующий шаг
    step_keys = [s["key"] for s in CHECKIN_STEPS]
    current_idx = step_keys.index(step_key) if step_key in step_keys else -1
    next_idx = current_idx + 1

    if next_idx < len(CHECKIN_STEPS):
        # Показываем следующий вопрос
        next_step = CHECKIN_STEPS[next_idx]
        await query.edit_message_text(
            next_step["question"],
            parse_mode="HTML",
            reply_markup=scale_keyboard(next_step["key"]),
        )
    else:
        # Все ответы собраны — считаем результат
        energy = checkin.get("energy", 5)
        stress = checkin.get("stress", 5)
        focus = checkin.get("focus", 5)

        result = interpret_results(energy, stress, focus)
        save_checkin(user_id, result)

        context.user_data.pop("checkin", None)
        context.user_data.pop("step", None)

        text = format_checkin_result(result)
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=result_keyboard(result["practice_key"]),
        )

    return True
