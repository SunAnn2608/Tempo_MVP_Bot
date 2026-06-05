"""
🎵 Tempo Bot — ВКонтакте
Полный порт TG-бота на VK LongPoll API.
Использует общие модули: task_manager, checkin, feedback, config, ai_analyzer
"""

import logging
import os
import sys
import random
import json
from pathlib import Path

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dotenv import load_dotenv

load_dotenv()

import config
from task_manager import (
    add_task, get_tasks_summary, clear_all_tasks, get_task_statistics,
    delete_task, toggle_task_done, edit_task_field,
    load_data, PRIORITY_ICON, PRIORITY_LABEL,
)
from feedback import (
    save_user_meta, handle_feedback_text as _fb_text,
    _save_feedback, format_feedback_for_admin, get_feedback_stats,
)
from checkin import interpret_results, save_checkin, format_checkin_result, get_checkin_history_text
from ai_analyzer import analyze_schedule, format_analysis_result, save_analysis_history

# ===== ЛОГИРОВАНИЕ =====

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("vk_bot.log", encoding="utf-8", mode="a"),
    ],
)
logger = logging.getLogger(__name__)

# ===== КОНФИГ =====

VK_TOKEN  = os.getenv("VK_TOKEN")
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", "0")).split(",")
    if x.strip().isdigit()
}

if not VK_TOKEN:
    logger.critical("❌ VK_TOKEN не найден!")
    sys.exit(1)

DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
PRIORITY_LABELS = {"high": "🔴 Высокий", "medium": "🟡 Средний", "low": "🟢 Низкий"}

# Состояние пользователей (in-memory, достаточно для MVP)
user_states: dict = {}   # user_id -> {"step": ..., "task_draft": ..., ...}


# ===== VK API ХЕЛПЕРЫ =====

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk         = vk_session.get_api()


def send(user_id: int, text: str, keyboard=None):
    """Отправить текстовое сообщение."""
    params = {
        "user_id":   user_id,
        "message":   text[:4096],
        "random_id": random.randint(0, 2**31),
    }
    if keyboard:
        params["keyboard"] = keyboard.get_keyboard()
    try:
        vk.messages.send(**params)
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения {user_id}: {e}")


def send_photo(user_id: int, photo_path: str, caption: str = ""):
    """Загрузить и отправить фото."""
    path = Path(photo_path)
    if not path.exists():
        logger.warning(f"Файл не найден: {photo_path}")
        send(user_id, "⚠️ Изображение недоступно")
        return
    try:
        upload     = vk_api.VkUpload(vk_session)
        photo_info = upload.photo_messages(str(path))[0]
        attachment = "photo{}_{}".format(photo_info["owner_id"], photo_info["id"])
        vk.messages.send(
            user_id=user_id,
            message=caption,
            attachment=attachment,
            random_id=random.randint(0, 2**31),
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")


def send_audio(user_id: int, audio_path: str, caption: str = ""):
    """Отправить аудио как документ через правильный peer_id."""
    path = Path(audio_path)
    if not path.exists():
        logger.warning(f"Файл не найден: {audio_path}")
        send(user_id, "⚠️ Аудио недоступно")
        return
    try:
        # peer_id для личных сообщений = user_id
        peer_id  = user_id
        upload   = vk_api.VkUpload(vk_session)
        doc_info = upload.document_message(
            str(path),
            peer_id=peer_id,
            title=path.stem,
        )
        attachment = "doc{}_{}".format(doc_info["owner_id"], doc_info["id"])
        vk.messages.send(
            user_id=user_id,
            message=caption,
            attachment=attachment,
            random_id=random.randint(0, 2**31),
        )
    except Exception as e:
        logger.error(f"Ошибка отправки аудио: {e}")
        # Отправляем текст с описанием практики как fallback
        send(user_id, f"🎧 Аудио временно недоступно. Практику можно найти в приложении.")


def get_state(user_id: int) -> dict:
    return user_states.setdefault(user_id, {})


def set_step(user_id: int, step: str):
    user_states.setdefault(user_id, {})["step"] = step


def clear_state(user_id: int):
    user_states[user_id] = {}


# ===== КЛАВИАТУРЫ =====

def kb_main() -> VkKeyboard:
    kb = VkKeyboard(one_time=False)
    kb.add_button("📋 Задачи",    color=VkKeyboardColor.PRIMARY)
    kb.add_button("🧘 Состояние", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🎧 Практики",  color=VkKeyboardColor.SECONDARY)
    kb.add_button("📥 Материалы", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("💬 Оставить отзыв", color=VkKeyboardColor.SECONDARY)
    return kb


def kb_tasks() -> VkKeyboard:
    kb = VkKeyboard(one_time=True)
    kb.add_button("➕ Добавить задачу",  color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("📄 Список задач",     color=VkKeyboardColor.SECONDARY)
    kb.add_button("✅ Выполнить",        color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("✏️ Редактировать",   color=VkKeyboardColor.SECONDARY)
    kb.add_button("🗑 Удалить",         color=VkKeyboardColor.NEGATIVE)
    kb.add_line()
    kb.add_button("📊 Статистика",      color=VkKeyboardColor.SECONDARY)
    kb.add_button("🧹 Очистить всё",    color=VkKeyboardColor.NEGATIVE)
    kb.add_line()
    kb.add_button("🤖 AI-анализ",       color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🏠 Главное меню",    color=VkKeyboardColor.PRIMARY)
    return kb


def kb_priority() -> VkKeyboard:
    kb = VkKeyboard(one_time=True)
    kb.add_button("🔴 Высокий",  color=VkKeyboardColor.NEGATIVE)
    kb.add_button("🟡 Средний",  color=VkKeyboardColor.SECONDARY)
    kb.add_button("🟢 Низкий",   color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("❌ Отмена",   color=VkKeyboardColor.SECONDARY)
    return kb


def kb_hours() -> VkKeyboard:
    kb = VkKeyboard(one_time=True)
    for h in range(1, 6):
        kb.add_button(str(h), color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    for h in range(6, 11):
        kb.add_button(str(h), color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("❌ Отмена", color=VkKeyboardColor.SECONDARY)
    return kb


def kb_days() -> VkKeyboard:
    kb = VkKeyboard(one_time=True)
    for i, day in enumerate(DAYS_RU):
        kb.add_button(day, color=VkKeyboardColor.SECONDARY)
        if i in (2, 5):
            kb.add_line()
    kb.add_line()
    kb.add_button("❌ Отмена", color=VkKeyboardColor.SECONDARY)
    return kb


def kb_practices() -> VkKeyboard:
    kb = VkKeyboard(one_time=True)
    for k, p in config.PRACTICES.items():
        kb.add_button(p["name"], color=VkKeyboardColor.SECONDARY)
        kb.add_line()
    kb.add_button("🏠 Главное меню", color=VkKeyboardColor.PRIMARY)
    return kb


def kb_scale() -> VkKeyboard:
    """Шкала 1–10 для чекина."""
    kb = VkKeyboard(one_time=True)
    for i in range(1, 6):
        kb.add_button(str(i), color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    for i in range(6, 11):
        kb.add_button(str(i), color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("❌ Отмена", color=VkKeyboardColor.SECONDARY)
    return kb


def kb_stars() -> VkKeyboard:
    """Оценка практики звёздами."""
    kb = VkKeyboard(one_time=True)
    for i in range(1, 6):
        kb.add_button("⭐" * i, color=VkKeyboardColor.SECONDARY)
        if i == 3:
            kb.add_line()
    kb.add_line()
    kb.add_button("Пропустить", color=VkKeyboardColor.SECONDARY)
    return kb


def kb_edit_field() -> VkKeyboard:
    kb = VkKeyboard(one_time=True)
    kb.add_button("🎯 Приоритет",    color=VkKeyboardColor.SECONDARY)
    kb.add_button("⏱️ Длительность", color=VkKeyboardColor.SECONDARY)
    kb.add_button("📅 День",         color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("❌ Отмена",       color=VkKeyboardColor.SECONDARY)
    return kb


def kb_tasks_list(tasks: list, action: str) -> VkKeyboard:
    """Нумерованный список задач для выбора."""
    kb = VkKeyboard(one_time=True)
    for i, t in enumerate(tasks[:8]):  # ВК лимит кнопок
        done = "✅" if t.get("done") else ""
        label = f"{i+1}. {done}{t['title'][:20]}"
        kb.add_button(label, color=VkKeyboardColor.SECONDARY)
        kb.add_line()
    kb.add_button("❌ Отмена", color=VkKeyboardColor.SECONDARY)
    return kb


# ===== ОБРАБОТЧИКИ =====

def handle_start(user_id: int, first_name: str):
    clear_state(user_id)
    save_user_meta(user_id, None, first_name)
    send(user_id,
        f"👋 Привет, {first_name}!\n\n"
        f"🎵 Я — Tempo Bot\n"
        f"{config.USP}\n\n"
        f"Выбери раздел:",
        kb_main(),
    )


def handle_tasks_menu(user_id: int):
    clear_state(user_id)
    send(user_id, "📋 Управление задачами:", kb_tasks())


def handle_task_list(user_id: int):
    send(user_id, get_tasks_summary(user_id))


def handle_task_stats(user_id: int):
    s = get_task_statistics(user_id)
    send(user_id,
        f"📊 Статистика задач:\n\n"
        f"📋 Всего: {s['total']}\n"
        f"✅ Выполнено: {s['done']}\n"
        f"⏳ Осталось: {s['pending']}\n"
        f"⏱️ Часов всего: {s['total_hours']} / выполнено: {s['done_hours']}\n\n"
        f"🔴 Высокий: {s['by_priority']['high']}\n"
        f"🟡 Средний: {s['by_priority']['medium']}\n"
        f"🟢 Низкий: {s['by_priority']['low']}"
    )


def handle_task_add_start(user_id: int):
    set_step(user_id, "task_title")
    send(user_id, "✏️ Шаг 1 из 4 — Введи название задачи:")


def handle_task_done_start(user_id: int):
    tasks = load_data().get("users", {}).get(str(user_id), {}).get("tasks", [])
    if not tasks:
        send(user_id, "📭 Нет задач")
        return
    set_step(user_id, "task_done_pick")
    send(user_id, "✅ Выбери задачу:", kb_tasks_list(tasks, "done"))


def handle_task_delete_start(user_id: int):
    tasks = load_data().get("users", {}).get(str(user_id), {}).get("tasks", [])
    if not tasks:
        send(user_id, "📭 Нет задач")
        return
    set_step(user_id, "task_del_pick")
    send(user_id, "🗑 Выбери задачу для удаления:", kb_tasks_list(tasks, "del"))


def handle_task_edit_start(user_id: int):
    tasks = load_data().get("users", {}).get(str(user_id), {}).get("tasks", [])
    if not tasks:
        send(user_id, "📭 Нет задач")
        return
    set_step(user_id, "task_edit_pick")
    send(user_id, "✏️ Выбери задачу для редактирования:", kb_tasks_list(tasks, "edit"))


def handle_practices_menu(user_id: int):
    clear_state(user_id)
    send(user_id, "🎧 Выбери практику:", kb_practices())


def handle_practice(user_id: int, practice_key: str):
    practice = config.PRACTICES.get(practice_key)
    if not practice:
        send(user_id, "❌ Практика не найдена")
        return
    send(user_id,
        f"🎧 {practice['name']}\n\n"
        f"⏱️ 5 минут\n"
        f"📝 {practice['desc']}"
    )
    send_photo(user_id, str(config.IMAGES_DIR / practice["image"]))
    send_audio(user_id, str(config.AUDIO_DIR / practice["audio"]))
    # Запрос оценки
    state = get_state(user_id)
    state["rating_practice_key"]  = practice_key
    state["rating_practice_name"] = practice["name"]
    state["step"] = "practice_rating"
    send(user_id, f"Как тебе практика «{practice['name']}»? Оцени:", kb_stars())


def handle_checkin_start(user_id: int):
    state = get_state(user_id)
    state["checkin"] = {}
    state["step"]    = "checkin_energy"
    send(user_id,
        "⚡ Шаг 1 из 3 — Энергия\n\n"
        "Как ты себя чувствуешь физически?\n"
        "1 — совсем без сил  /  10 — полон энергии",
        kb_scale(),
    )


def handle_feedback_start(user_id: int):
    set_step(user_id, "feedback_text")
    send(user_id,
        "💬 Оставить отзыв\n\n"
        "Напиши что думаешь о боте: что нравится, что мешает, чего не хватает.\n\n"
        "Мы читаем каждый отзыв 🙏"
    )


def handle_ai_start(user_id: int):
    set_step(user_id, "ai_input")
    send(user_id,
        "🤖 AI-анализ расписания\n\n"
        "Отправь расписание текстом.\n"
        "Пример: Понедельник: Работа 8ч, Спорт 1ч"
    )


# ===== ГЛАВНЫЙ РОУТЕР =====

def route(user_id: int, first_name: str, text: str):
    text  = text.strip()
    state = get_state(user_id)
    step  = state.get("step")

    logger.info(f"VK от {user_id} ({first_name}): '{text}' (step={step})")

    # ── Старт / меню ──────────────────────────────────────────────
    if text.lower() in ("начать", "старт", "/start", "привет", "start"):
        handle_start(user_id, first_name)
        return

    if text == "🏠 Главное меню" or text.lower() == "меню":
        clear_state(user_id)
        send(user_id, "🏠 Главное меню:", kb_main())
        return

    if text == "❌ Отмена":
        clear_state(user_id)
        send(user_id, "❌ Отменено", kb_main())
        return

    # ── Главное меню ──────────────────────────────────────────────
    if text == "📋 Задачи":
        handle_tasks_menu(user_id)
        return
    if text == "🎧 Практики":
        handle_practices_menu(user_id)
        return
    if text == "🧘 Состояние":
        handle_checkin_start(user_id)
        return
    if text == "💬 Оставить отзыв":
        handle_feedback_start(user_id)
        return
    if text == "📥 Материалы":
        send(user_id, "⏳ Материалы в подготовке. Загляните позже!")
        return

    # ── Меню задач ────────────────────────────────────────────────
    if text == "➕ Добавить задачу":
        handle_task_add_start(user_id)
        return
    if text == "📄 Список задач":
        handle_task_list(user_id)
        return
    if text == "✅ Выполнить":
        handle_task_done_start(user_id)
        return
    if text == "✏️ Редактировать":
        handle_task_edit_start(user_id)
        return
    if text == "🗑 Удалить":
        handle_task_delete_start(user_id)
        return
    if text == "📊 Статистика":
        handle_task_stats(user_id)
        return
    if text == "🧹 Очистить всё":
        clear_all_tasks(user_id)
        send(user_id, "🧹 Все задачи удалены", kb_tasks())
        return
    if text == "🤖 AI-анализ":
        handle_ai_start(user_id)
        return

    # ── Практики ─────────────────────────────────────────────────
    for key, p in config.PRACTICES.items():
        if text == p["name"]:
            handle_practice(user_id, key)
            return

    # ── Оценка практики ──────────────────────────────────────────
    if step == "practice_rating":
        stars_map = {"⭐": 1, "⭐⭐": 2, "⭐⭐⭐": 3, "⭐⭐⭐⭐": 4, "⭐⭐⭐⭐⭐": 5}
        if text == "Пропустить":
            clear_state(user_id)
            send(user_id, "👌 Хорошо!", kb_main())
            return
        if text in stars_map:
            stars = stars_map[text]
            _save_feedback(user_id, "practice_rating", {
                "practice_key":  state.get("rating_practice_key"),
                "practice_name": state.get("rating_practice_name"),
                "stars":         stars,
            })
            clear_state(user_id)
            comment = {5: "Отлично!", 4: "Хорошо!", 3: "Нормально", 2: "Надо улучшить", 1: "Не понравилось"}.get(stars, "")
            send(user_id, f"{'⭐' * stars} {comment}\n\nСпасибо! 🙏", kb_main())
            return

    # ── Чек-ин ────────────────────────────────────────────────────
    if step in ("checkin_energy", "checkin_stress", "checkin_focus"):
        if not text.isdigit() or not (1 <= int(text) <= 10):
            send(user_id, "Введи число от 1 до 10:", kb_scale())
            return
        val     = int(text)
        checkin = state.get("checkin", {})

        if step == "checkin_energy":
            checkin["energy"] = val
            state["checkin"]  = checkin
            state["step"]     = "checkin_stress"
            send(user_id,
                "🌊 Шаг 2 из 3 — Стресс\n\n"
                "Какой уровень напряжения?\n"
                "1 — полностью спокоен  /  10 — на пределе",
                kb_scale(),
            )
        elif step == "checkin_stress":
            checkin["stress"] = val
            state["checkin"]  = checkin
            state["step"]     = "checkin_focus"
            send(user_id,
                "🎯 Шаг 3 из 3 — Фокус\n\n"
                "Насколько легко сосредоточиться?\n"
                "1 — мысли разбегаются  /  10 — в потоке",
                kb_scale(),
            )
        elif step == "checkin_focus":
            checkin["focus"] = val
            result = interpret_results(checkin["energy"], checkin["stress"], val)
            save_checkin(user_id, result)
            clear_state(user_id)
            text_out = format_checkin_result(result)
            # Убираем HTML-теги для ВК
            import re
            text_out = re.sub(r"<[^>]+>", "", text_out)
            practice = config.PRACTICES.get(result["practice_key"])
            if practice:
                text_out += f"\n\n👉 Рекомендую: {practice['name']}"
            send(user_id, text_out, kb_main())
        return

    # ── Добавление задачи ─────────────────────────────────────────
    if step == "task_title":
        if len(text) < 2:
            send(user_id, "❌ Слишком короткое название, попробуй ещё раз:")
            return
        state["task_draft"] = {"title": text}
        state["step"]       = "task_priority"
        send(user_id, f"✅ Название: {text}\n\nШаг 2 из 4 — Выбери приоритет:", kb_priority())
        return

    if step == "task_priority":
        priority_map = {"🔴 Высокий": "high", "🟡 Средний": "medium", "🟢 Низкий": "low"}
        if text not in priority_map:
            send(user_id, "Выбери приоритет кнопкой:", kb_priority())
            return
        state["task_draft"]["priority"] = priority_map[text]
        state["step"] = "task_hours"
        send(user_id, f"✅ Приоритет: {text}\n\nШаг 3 из 4 — Сколько часов займёт задача?", kb_hours())
        return

    if step == "task_hours":
        if not text.isdigit() or not (1 <= int(text) <= 10):
            send(user_id, "Выбери количество часов кнопкой:", kb_hours())
            return
        state["task_draft"]["duration_hours"] = int(text)
        state["step"] = "task_day"
        send(user_id, f"✅ Длительность: {text} ч\n\nШаг 4 из 4 — На какой день?", kb_days())
        return

    if step == "task_day":
        if text not in DAYS_RU:
            send(user_id, "Выбери день кнопкой:", kb_days())
            return
        state["task_draft"]["day"] = text
        draft = state["task_draft"]
        try:
            add_task(user_id, draft)
            p_label = PRIORITY_LABELS.get(draft.get("priority", "medium"), "")
            clear_state(user_id)
            send(user_id,
                f"✅ Задача добавлена!\n\n"
                f"📌 {draft['title']}\n"
                f"📅 {text}  ⏱️ {draft['duration_hours']}ч  {p_label}",
                kb_tasks(),
            )
        except Exception as e:
            send(user_id, f"❌ Ошибка: {e}")
        return

    # ── Выбор задачи для выполнения ───────────────────────────────
    if step == "task_done_pick":
        tasks = load_data().get("users", {}).get(str(user_id), {}).get("tasks", [])
        for i, t in enumerate(tasks[:8]):
            done = "✅" if t.get("done") else ""
            if text == f"{i+1}. {done}{t['title'][:20]}":
                updated = toggle_task_done(user_id, i)
                status  = "✅ Выполнена" if updated.get("done") else "◻️ Возвращена"
                clear_state(user_id)
                send(user_id, f"{status}: {updated['title']}", kb_tasks())
                return
        send(user_id, "Выбери задачу кнопкой:", kb_tasks_list(tasks, "done"))
        return

    # ── Выбор задачи для удаления ─────────────────────────────────
    if step == "task_del_pick":
        tasks = load_data().get("users", {}).get(str(user_id), {}).get("tasks", [])
        for i, t in enumerate(tasks[:8]):
            done = "✅" if t.get("done") else ""
            if text == f"{i+1}. {done}{t['title'][:20]}":
                delete_task(user_id, i)
                clear_state(user_id)
                send(user_id, "✅ Задача удалена", kb_tasks())
                return
        send(user_id, "Выбери задачу кнопкой:", kb_tasks_list(tasks, "del"))
        return

    # ── Выбор задачи для редактирования ──────────────────────────
    if step == "task_edit_pick":
        tasks = load_data().get("users", {}).get(str(user_id), {}).get("tasks", [])
        for i, t in enumerate(tasks[:8]):
            done = "✅" if t.get("done") else ""
            if text == f"{i+1}. {done}{t['title'][:20]}":
                state["edit_task_idx"] = i
                state["step"]          = "task_edit_field"
                send(user_id,
                    f"✏️ Редактировать: {t['title']}\n"
                    f"Приоритет: {PRIORITY_LABELS.get(t.get('priority','medium'))}  "
                    f"|  {t.get('duration_hours',1)}ч  |  {t.get('day','—')}\n\n"
                    f"Что изменить?",
                    kb_edit_field(),
                )
                return
        send(user_id, "Выбери задачу кнопкой:", kb_tasks_list(tasks, "edit"))
        return

    if step == "task_edit_field":
        if text == "🎯 Приоритет":
            state["edit_field"] = "priority"
            state["step"]       = "task_edit_value"
            send(user_id, "Выбери новый приоритет:", kb_priority())
        elif text == "⏱️ Длительность":
            state["edit_field"] = "duration_hours"
            state["step"]       = "task_edit_value"
            send(user_id, "Выбери новую длительность:", kb_hours())
        elif text == "📅 День":
            state["edit_field"] = "day"
            state["step"]       = "task_edit_value"
            send(user_id, "Выбери новый день:", kb_days())
        return

    if step == "task_edit_value":
        field = state.get("edit_field")
        idx   = state.get("edit_task_idx", -1)
        priority_map = {"🔴 Высокий": "high", "🟡 Средний": "medium", "🟢 Низкий": "low"}

        if field == "priority" and text in priority_map:
            edit_task_field(user_id, idx, "priority", priority_map[text])
            clear_state(user_id)
            send(user_id, f"✅ Приоритет обновлён: {text}", kb_tasks())
        elif field == "duration_hours" and text.isdigit():
            edit_task_field(user_id, idx, "duration_hours", int(text))
            clear_state(user_id)
            send(user_id, f"✅ Длительность обновлена: {text} ч", kb_tasks())
        elif field == "day" and text in DAYS_RU:
            edit_task_field(user_id, idx, "day", text)
            clear_state(user_id)
            send(user_id, f"✅ День обновлён: {text}", kb_tasks())
        else:
            send(user_id, "Выбери значение кнопкой")
        return

    # ── Обратная связь ────────────────────────────────────────────
    if step == "feedback_text":
        if len(text.strip()) >= 3:
            _save_feedback(user_id, "free_text", {"text": text.strip()})
            clear_state(user_id)
            send(user_id, "💙 Спасибо! Твой отзыв получен 🙏", kb_main())
        return

    # ── AI-анализ ─────────────────────────────────────────────────
    if step == "ai_input":
        if len(text.strip()) < 20:
            send(user_id, "❌ Слишком мало данных. Опиши расписание подробнее.")
            return
        send(user_id, "🤖 Анализирую...")
        try:
            result    = analyze_schedule(text)
            formatted = format_analysis_result(result)
            import re
            formatted = re.sub(r"<[^>]+>", "", formatted)
            send(user_id, formatted)
            save_analysis_history(user_id, text, result)
        except Exception as e:
            send(user_id, f"❌ Ошибка при анализе: {e}")
        clear_state(user_id)
        return

    # ── Команды админа ────────────────────────────────────────────
    if text.startswith("/feedback_admin") and user_id in ADMIN_IDS:
        parts = text.split()
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20
        result_text = format_feedback_for_admin(limit)
        import re
        result_text = re.sub(r"<[^>]+>", "", result_text)
        for chunk in [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]:
            send(user_id, chunk)
        return

    if text == "/feedback_stats" and user_id in ADMIN_IDS:
        import re
        stats = re.sub(r"<[^>]+>", "", get_feedback_stats())
        send(user_id, stats)
        return

    # ── Напоминания вкл/выкл ─────────────────────────────────────
    if text.lower() in ("напоминания вкл", "/reminders_on"):
        toggle_vk_reminders(user_id, True)
        send(user_id, "🔔 Напоминания включены! Буду писать в 10:00, 14:00 и 17:00", kb_main())
        return
    if text.lower() in ("напоминания выкл", "/reminders_off"):
        toggle_vk_reminders(user_id, False)
        send(user_id, "🔕 Напоминания выключены", kb_main())
        return

    # ── Дефолт ────────────────────────────────────────────────────
    send(user_id, "💡 Используй кнопки меню. Напиши «старт» чтобы начать.", kb_main())


# ===== ТОЧКА ВХОДА =====

# ===== НАПОМИНАНИЯ =====

import threading
import time
from datetime import datetime


REMINDER_TIMES = ["10:00", "14:00", "17:00"]

REMINDER_MESSAGES = [
    "🌅 Доброе утро! Как твоё состояние сегодня?\nНапиши «🧘 Состояние» чтобы пройти чек-ин.",
    "☀️ Середина дня — самое время сделать паузу.\nВыбери практику: «🎧 Практики»",
    "🌆 Вечер! Как прошёл день?\nПройди чек-ин или послушай практику для расслабления.",
]


def get_reminder_users() -> list:
    """Возвращает список user_id у которых включены напоминания."""
    data  = load_data()
    users = []
    for uid, udata in data.get("users", {}).items():
        if udata.get("reminders_enabled", True):  # по умолчанию включены
            try:
                users.append(int(uid))
            except ValueError:
                pass
    return users


def toggle_vk_reminders(user_id: int, enabled: bool):
    data = load_data()
    uid  = str(user_id)
    data.setdefault("users", {}).setdefault(uid, {})["reminders_enabled"] = enabled
    from task_manager import save_data
    save_data(data)


def reminders_loop():
    """Бесконечный цикл — каждую минуту проверяет время и рассылает напоминания."""
    logger.info("⏰ Поток напоминаний запущен")
    sent_today: set = set()  # (user_id, time_str) — чтобы не слать дважды

    while True:
        try:
            now      = datetime.now()
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%Y-%m-%d")

            # Сбрасываем отправленные в полночь
            if time_str == "00:00":
                sent_today.clear()

            if time_str in REMINDER_TIMES:
                msg_idx = REMINDER_TIMES.index(time_str)
                message = REMINDER_MESSAGES[msg_idx]
                users   = get_reminder_users()

                for uid in users:
                    key = (uid, time_str, date_str)
                    if key not in sent_today:
                        try:
                            send(uid, message, kb_main())
                            sent_today.add(key)
                            logger.info(f"Напоминание отправлено: {uid} в {time_str}")
                        except Exception as e:
                            logger.error(f"Ошибка напоминания {uid}: {e}")

        except Exception as e:
            logger.error(f"Ошибка в потоке напоминаний: {e}")

        time.sleep(60)  # проверяем каждую минуту


def start_reminders_thread():
    t = threading.Thread(target=reminders_loop, daemon=True)
    t.start()
    return t


# ===== ТОЧКА ВХОДА =====

def main():
    logger.info("🎵 Tempo VK Bot запускается...")
    start_reminders_thread()
    logger.info("⏰ Напоминания активированы")
    longpoll = VkLongPoll(vk_session)
    logger.info("✅ VK Bot готов к работе!")
    print("🚀 Tempo VK Bot запущен!")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            try:
                user_id    = event.user_id
                text       = event.text or ""
                user_info  = vk.users.get(user_ids=user_id)[0]
                first_name = user_info.get("first_name", "друг")
                route(user_id, first_name, text)
            except Exception as e:
                logger.error(f"Ошибка обработки события: {e}", exc_info=True)


if __name__ == "__main__":
    main()
