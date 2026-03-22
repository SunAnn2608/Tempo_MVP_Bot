import json
import os
from datetime import datetime
from typing import Dict, Optional

import config

DATA_FILE = 'data.json'


# ===== БАЗА =====

def load_data() -> Dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'users': {}}
    return {'users': {}}


def save_data(data: Dict):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===== ПОЛЬЗОВАТЕЛЬ =====

def get_user_data(user_id: int) -> Dict:
    data = load_data()
    user_key = str(user_id)

    if user_key not in data['users']:
        data['users'][user_key] = {
            'tasks': {'daily': {}, 'weekly': {}},
            'settings': {'planning_mode': 'weekly', 'reminders_enabled': True},
            'stats': {
                'tasks_added': 0,
                'tasks_completed': 0,
                'tasks_edited': 0,
                'tasks_deleted': 0
            }
        }
        save_data(data)

    return data['users'][user_key]


def get_user_tasks(user_id: int, planning_mode: str = 'weekly') -> Dict:
    user = get_user_data(user_id)
    return user['tasks'].get(planning_mode, {})


# ===== CRUD =====

def add_task(user_id: int, task_data: Dict, planning_mode: str = 'weekly') -> Dict:
    data = load_data()
    user_key = str(user_id)

    if user_key not in data['users']:
        data['users'][user_key] = get_user_data(user_id)

    user = data['users'][user_key]
    tasks = user['tasks'].setdefault(planning_mode, {})

    # ===== ПРОВЕРКА ПЕРЕГРУЗА =====
    day = task_data.get('day', 'Monday')
    day_tasks = [t for t in tasks.values() if t.get('day') == day]

    if len(day_tasks) >= config.MAX_TASKS_PER_DAY:
        return {
            'success': False,
            'error': "⚠️ Слишком много задач на этот день.\nПопробуй распределить нагрузку."
        }

    # ===== ID =====
    task_id = max([int(k) for k in tasks.keys()], default=0) + 1

    # ===== SAFE DURATION =====
    try:
        duration = float(task_data.get('duration_hours', 1))
    except:
        duration = 1

    task = {
        'id': task_id,
        'title': task_data.get('title', 'Без названия'),
        'day': day,
        'duration_hours': duration,
        'priority': task_data.get('priority', 'medium'),
        'completed': False,
        'created_at': datetime.now().isoformat(),
        'updated_at': None
    }

    tasks[str(task_id)] = task

    stats = user.setdefault('stats', {})
    stats['tasks_added'] = stats.get('tasks_added', 0) + 1

    save_data(data)

    return {'success': True, 'task_id': task_id, 'message': f"✅ Задача #{task_id} добавлена"}


def get_task(user_id: int, task_id: int, planning_mode: str = 'weekly') -> Optional[Dict]:
    tasks = get_user_tasks(user_id, planning_mode)
    return tasks.get(str(task_id))


def edit_task(user_id: int, task_id: int, updates: Dict, planning_mode: str = 'weekly') -> Dict:
    data = load_data()
    user_key = str(user_id)

    if user_key not in data['users']:
        return {'success': False, 'error': 'Пользователь не найден'}

    tasks = data['users'][user_key]['tasks'].get(planning_mode, {})
    task = tasks.get(str(task_id))

    if not task:
        return {'success': False, 'error': f'Задача #{task_id} не найдена'}

    for key in ['title', 'day', 'duration_hours', 'priority', 'completed']:
        if key in updates:
            task[key] = updates[key]

    task['updated_at'] = datetime.now().isoformat()

    stats = data['users'][user_key].setdefault('stats', {})
    stats['tasks_edited'] = stats.get('tasks_edited', 0) + 1

    save_data(data)

    return {'success': True, 'message': f"✅ Задача #{task_id} обновлена"}


def delete_task(user_id: int, task_id: int, planning_mode: str = 'weekly') -> Dict:
    data = load_data()
    user_key = str(user_id)

    tasks = data['users'].get(user_key, {}).get('tasks', {}).get(planning_mode, {})
    task = tasks.pop(str(task_id), None)

    if not task:
        return {'success': False, 'error': 'Задача не найдена'}

    stats = data['users'][user_key].setdefault('stats', {})
    stats['tasks_deleted'] = stats.get('tasks_deleted', 0) + 1

    save_data(data)

    return {'success': True, 'message': "🗑️ Задача удалена"}


def mark_task_completed(user_id: int, task_id: int, planning_mode: str = 'weekly') -> Dict:
    result = edit_task(user_id, task_id, {'completed': True}, planning_mode)

    if result['success']:
        data = load_data()
        stats = data['users'][str(user_id)].setdefault('stats', {})
        stats['tasks_completed'] = stats.get('tasks_completed', 0) + 1
        save_data(data)

    return result


# ===== СВОДКА =====

def get_tasks_summary(user_id: int, planning_mode: str = 'weekly') -> str:
    tasks = get_user_tasks(user_id, planning_mode)

    if not tasks:
        return "📭 Нет задач"

    summary = "📋 Ваши задачи:\n\n"
    total = 0

    for task in tasks.values():
        status = '✅' if task.get('completed') else '⏳'
        summary += f"{status} #{task['id']} {task['title']} ({task['duration_hours']}ч)\n"
        total += float(task.get('duration_hours', 0))

    summary += f"\n⏱️ Всего: {total} ч"

    return summary


def clear_all_tasks(user_id: int, planning_mode: str = None) -> Dict:
    data = load_data()
    user_key = str(user_id)

    if planning_mode:
        data['users'][user_key]['tasks'][planning_mode] = {}
    else:
        data['users'][user_key]['tasks'] = {'daily': {}, 'weekly': {}}

    save_data(data)

    return {'success': True, 'message': "🧹 Очищено"}