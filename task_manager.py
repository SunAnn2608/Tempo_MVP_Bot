"""
📋 Tempo Bot — Управление задачами
ТРЕБОВАНИЯ: ✅ Словари ✅ Функции ✅ Файлы
"""

import json
import os
from pathlib import Path
from datetime import datetime

import config


def ensure_data_dir():
    """Создание папки data, если не существует (ТРЕБОВАНИЕ 4)"""
    config.DATA_DIR.mkdir(exist_ok=True)


def load_data():
    """Чтение данных из JSON-файла (ТРЕБОВАНИЕ 4)"""
    ensure_data_dir()
    
    # ===== ТРЕБОВАНИЕ 1: УСЛОВИЯ =====
    if config.DATA_FILE.exists():
        try:
            with open(config.DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}}
    
    return {"users": {}}


def save_data(data):
    """Сохранение данных в JSON-файл (ТРЕБОВАНИЕ 4)"""
    ensure_data_dir()
    
    try:
        with open(config.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def add_task(user_id, task):
    """Добавление задачи пользователю (ТРЕБОВАНИЕ 2+3)"""
    data = load_data()
    user_id = str(user_id)
    
    # ===== ТРЕБОВАНИЕ 1: УСЛОВИЯ =====
    if user_id not in data["users"]:
        data["users"][user_id] = {"tasks": []}
    
    # Добавляем метаданные к задаче
    task_with_meta = {
        "title": task.get("title", "Без названия"),
        "duration_hours": task.get("duration_hours", 1),
        "day": task.get("day", "Monday"),
        "priority": task.get("priority", "medium"),
        "created_at": datetime.now().isoformat()
    }
    
    data["users"][user_id]["tasks"].append(task_with_meta)
    save_data(data)
    
    return {"message": "✅ Задача добавлена", "task": task_with_meta}


def get_tasks_summary(user_id):
    """Получение сводки по задачам (ТРЕБОВАНИЕ 3)"""
    data = load_data()
    user_id = str(user_id)
    
    # ===== ТРЕБОВАНИЕ 2: СЛОВАРИ =====
    tasks = data["users"].get(user_id, {}).get("tasks", [])
    
    # ===== ТРЕБОВАНИЕ 1: УСЛОВИЯ =====
    if not tasks:
        return "📭 Нет задач. Добавьте первую!"
    
    text = "📋 Ваши задачи:\n\n"
    for i, t in enumerate(tasks, 1):
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority"), "⚪")
        text += f"{i}. {priority_icon} {t['title']} ({t.get('duration_hours', 1)}ч)\n"
    
    total = sum(t.get("duration_hours", 1) for t in tasks)
    text += f"\n⏱️ Всего: {total} ч"
    
    # ===== УСЛОВИЕ: предупреждение о перегрузке =====
    if total > config.MAX_TASKS_PER_DAY:
        text += "\n\n⚠️ Нагрузка выше нормы!"
    
    return text


def clear_all_tasks(user_id):
    """Очистка всех задач пользователя (ТРЕБОВАНИЕ 1+3+4)"""
    data = load_data()
    user_id = str(user_id)
    
    # ===== ТРЕБОВАНИЕ 1: УСЛОВИЯ =====
    if user_id in data["users"]:
        data["users"][user_id]["tasks"] = []
        save_data(data)
        return True
    return False


def get_task_statistics(user_id):
    """Статистика по задачам (ТРЕБОВАНИЕ 3)"""
    data = load_data()
    user_id = str(user_id)
    
    tasks = data["users"].get(user_id, {}).get("tasks", [])
    
    return {
        "total": len(tasks),
        "total_hours": sum(t.get("duration_hours", 1) for t in tasks),
        "by_priority": {
            "high": sum(1 for t in tasks if t.get("priority") == "high"),
            "medium": sum(1 for t in tasks if t.get("priority") == "medium"),
            "low": sum(1 for t in tasks if t.get("priority") == "low"),
        }
    }
