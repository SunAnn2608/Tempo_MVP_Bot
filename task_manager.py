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
    config.DATA_DIR.mkdir(exist_ok=True)


def load_data():
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
    ensure_data_dir()
    
    try:
        with open(config.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения data.json: {e}")
        return False


def add_task(user_id, task):
    try:
        logger.info(f"add_task вызван для user_id={user_id}, task={task}")
        
        data = load_data()
        user_id = str(user_id)
        
        if user_id not in data["users"]:
            logger.info(f"Создаю нового пользователя {user_id}")
            data["users"][user_id] = {"tasks": []}
        
        task_with_meta = {
            "title": task.get("title", "Без названия"),
            "duration_hours": task.get("duration_hours", 1),
            "day": task.get("day", "Monday"),
            "priority": task.get("priority", "medium"),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Добавляю задачу: {task_with_meta}")
        
        data["users"][user_id]["tasks"].append(task_with_meta)
        
        save_result = save_data(data)
        logger.info(f"save_data вернул: {save_result}")
        
        if not save_result:
            raise Exception("Не удалось сохранить данные")
        
        return {"message": "✅ Задача добавлена", "task": task_with_meta}
        
    except Exception as e:
        logger.error(f"Ошибка в add_task: {e}", exc_info=True)
        raise
