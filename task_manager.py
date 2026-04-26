"""
📋 Tempo Bot — Управление задачами
"""

import json
import logging
from pathlib import Path
from datetime import datetime

import config

logger = logging.getLogger(__name__)


def ensure_data_dir():
    """Создание папки data, если не существует"""
    config.DATA_DIR.mkdir(exist_ok=True)


def load_data():
    """Чтение данных из JSON-файла"""
    ensure_data_dir()
    
    if config.DATA_FILE.exists():
        try:
            with open(config.DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Ошибка чтения data.json — файл повреждён")
            return {"users": {}}
        except Exception as e:
            logger.error(f"Ошибка загрузки data.json: {e}")
            return {"users": {}}
    
    return {"users": {}}


def save_data(data):
    """Сохранение данных в JSON-файл"""
    ensure_data_dir()
    
    try:
        with open(config.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения data.json: {e}")
        return False


def add_task(user_id, task):
    """Добавление задачи пользователю"""
    try:
        logger.info(f"add_task вызван для user_id={user_id}, task={task}")
        
        data = load_data()
        user_id = str(user_id)
        
        # Создаём пользователя, если не существует
        if user_id not in data["users"]:
            logger.info(f"Создаю нового пользователя {user_id}")
            data["users"][user_id] = {}
        
        # Гарантируем наличие ключа "tasks"
        if "tasks" not in data["users"][user_id]:
            logger.info(f"Создаю список задач для пользователя {user_id}")
            data["users"][user_id]["tasks"] = []
        
        # Создаём задачу
        task_with_meta = {
            "title": task.get("title", "Без названия"),
            "duration_hours": task.get("duration_hours", 1),
            "day": task.get("day", "Monday"),
            "priority": task.get("priority", "medium"),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Добавляю задачу: {task_with_meta}")
        
        # Добавляем задачу
        data["users"][user_id]["tasks"].append(task_with_meta)
        
        # Сохраняем
        save_result = save_data(data)
        logger.info(f"save_data вернул: {save_result}")
        
        if not save_result:
            raise Exception("Не удалось сохранить данные")
        
        return {"message": "✅ Задача добавлена", "task": task_with_meta}
        
    except KeyError as e:
        logger.error(f"KeyError в add_task: {e}", exc_info=True)
        raise Exception(f"Отсутствует ключ в данных: {e}")
    except Exception as e:
        logger.error(f"Ошибка в add_task: {e}", exc_info=True)
        raise


def get_tasks_summary(user_id):
    """Получение сводки по задачам"""
    data = load_data()
    user_id = str(user_id)
    
    # Безопасное получение задач
    user_data = data["users"].get(user_id, {})
    tasks = user_data.get("tasks", [])
    
    if not tasks:
        return "📭 Нет задач. Добавьте первую!"
    
    text = "📋 Ваши задачи:\n\n"
    for i, t in enumerate(tasks, 1):
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority"), "⚪")
        text += f"{i}. {priority_icon} {t['title']} ({t.get('duration_hours', 1)}ч)\n"
    
    total = sum(t.get("duration_hours", 1) for t in tasks)
    text += f"\n⏱️ Всего: {total} ч"
    
    if total > config.MAX_TASKS_PER_DAY:
        text += "\n\n⚠️ Нагрузка выше нормы!"
    
    return text


def clear_all_tasks(user_id):
    """Очистка всех задач пользователя"""
    data = load_data()
    user_id = str(user_id)
    
    if user_id in data["users"]:
        # Гарантируем наличие ключа tasks
        if "tasks" not in data["users"][user_id]:
            data["users"][user_id]["tasks"] = []
        else:
            data["users"][user_id]["tasks"] = []
        save_data(data)
        return True
    return False


def get_task_statistics(user_id):
    """Статистика по задачам"""
    data = load_data()
    user_id = str(user_id)
    
    # Безопасное получение
    user_data = data["users"].get(user_id, {})
    tasks = user_data.get("tasks", [])
    
    return {
        "total": len(tasks),
        "total_hours": sum(t.get("duration_hours", 1) for t in tasks),
        "by_priority": {
            "high": sum(1 for t in tasks if t.get("priority") == "high"),
            "medium": sum(1 for t in tasks if t.get("priority") == "medium"),
            "low": sum(1 for t in tasks if t.get("priority") == "low"),
        }
    }
