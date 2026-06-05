"""
📋 Tempo Bot — Управление задачами

Пошаговое добавление: название → приоритет → часы → день недели.
Поддержка: отметка выполненных, редактирование полей, статистика.
Хранение: data/data.json, ключ по user_id.
"""

import json
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)

PRIORITY_ICON  = {"high": "🔴", "medium": "🟡", "low": "🟢"}
PRIORITY_LABEL = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}

# ===== JSON-ХРАНИЛИЩЕ =====

def ensure_data_dir():
    config.DATA_DIR.mkdir(exist_ok=True)


def load_data() -> dict:
    ensure_data_dir()
    if config.DATA_FILE.exists():
        try:
            with open(config.DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("data.json повреждён — сброс")
        except Exception as e:
            logger.error(f"Ошибка загрузки data.json: {e}")
    return {"users": {}}


def save_data(data: dict) -> bool:
    ensure_data_dir()
    try:
        with open(config.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения data.json: {e}")
        return False


def _get_user_tasks(data: dict, user_id: str) -> list:
    return data.setdefault("users", {}).setdefault(user_id, {}).setdefault("tasks", [])


# ===== CRUD ЗАДАЧ =====

def add_task(user_id, task: dict) -> dict:
    data = load_data()
    uid = str(user_id)
    tasks = _get_user_tasks(data, uid)

    task_record = {
        "title":          task.get("title", "Без названия").strip(),
        "priority":       task.get("priority", "medium"),
        "duration_hours": int(task.get("duration_hours", 1)),
        "day":            task.get("day", "Понедельник"),
        "done":           False,
        "created_at":     datetime.now().isoformat(),
    }
    tasks.append(task_record)

    if not save_data(data):
        raise RuntimeError("Не удалось сохранить задачу")

    logger.info(f"Задача добавлена для {uid}: {task_record['title']}")
    return {"message": "✅ Задача добавлена", "task": task_record}


def toggle_task_done(user_id, index: int) -> dict | None:
    """
    Переключает done True/False.
    Возвращает обновлённую задачу или None если индекс не найден.
    """
    data = load_data()
    tasks = _get_user_tasks(data, str(user_id))
    if not (0 <= index < len(tasks)):
        return None
    tasks[index]["done"] = not tasks[index].get("done", False)
    if tasks[index]["done"]:
        tasks[index]["done_at"] = datetime.now().isoformat()
    else:
        tasks[index].pop("done_at", None)
    save_data(data)
    return tasks[index]


def edit_task_field(user_id, index: int, field: str, value) -> bool:
    """Обновляет одно поле задачи (priority | duration_hours | day | title)."""
    allowed = {"priority", "duration_hours", "day", "title"}
    if field not in allowed:
        return False
    data = load_data()
    tasks = _get_user_tasks(data, str(user_id))
    if not (0 <= index < len(tasks)):
        return False
    tasks[index][field] = value
    tasks[index]["updated_at"] = datetime.now().isoformat()
    save_data(data)
    logger.info(f"Задача {index} обновлена: {field}={value}")
    return True


def delete_task(user_id, index: int) -> bool:
    data = load_data()
    tasks = _get_user_tasks(data, str(user_id))
    if 0 <= index < len(tasks):
        removed = tasks.pop(index)
        save_data(data)
        logger.info(f"Задача удалена: {removed['title']}")
        return True
    return False


def clear_all_tasks(user_id) -> bool:
    data = load_data()
    uid = str(user_id)
    if uid in data.get("users", {}):
        data["users"][uid]["tasks"] = []
        save_data(data)
        return True
    return False


# ===== ОТОБРАЖЕНИЕ =====

def _task_line(i: int, t: dict, show_index: bool = True) -> str:
    icon  = PRIORITY_ICON.get(t.get("priority"), "⚪")
    done  = "✅" if t.get("done") else "◻️"
    title = t["title"]
    if t.get("done"):
        title = f"<s>{title}</s>"
    prefix = f"{i}. " if show_index else ""
    return (
        f"{prefix}{done} {icon} {title}  "
        f"<i>{t.get('duration_hours', 1)}ч · {t.get('day', '—')}</i>"
    )


def get_tasks_summary(user_id) -> str:
    data = load_data()
    tasks = _get_user_tasks(data, str(user_id))

    if not tasks:
        return "📭 Нет задач. Добавьте первую!"

    lines = ["📋 <b>Ваши задачи:</b>\n"]
    for i, t in enumerate(tasks, 1):
        lines.append(_task_line(i, t))

    pending = [t for t in tasks if not t.get("done")]
    done    = [t for t in tasks if t.get("done")]
    total_h = sum(t.get("duration_hours", 1) for t in pending)

    lines.append(f"\n✅ Выполнено: {len(done)} / {len(tasks)}")
    lines.append(f"⏱️ Осталось: {total_h} ч")

    if total_h > config.MAX_TASKS_PER_DAY:
        lines.append("⚠️ Нагрузка выше нормы — подумай о переносе задач")

    return "\n".join(lines)


def get_task_statistics(user_id) -> dict:
    data  = load_data()
    tasks = _get_user_tasks(data, str(user_id))
    done  = [t for t in tasks if t.get("done")]
    return {
        "total":       len(tasks),
        "done":        len(done),
        "pending":     len(tasks) - len(done),
        "total_hours": sum(t.get("duration_hours", 1) for t in tasks),
        "done_hours":  sum(t.get("duration_hours", 1) for t in done),
        "by_priority": {
            "high":   sum(1 for t in tasks if t.get("priority") == "high"),
            "medium": sum(1 for t in tasks if t.get("priority") == "medium"),
            "low":    sum(1 for t in tasks if t.get("priority") == "low"),
        },
    }
