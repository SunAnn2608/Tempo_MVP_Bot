"""
📋 Tempo Bot — Менеджер задач (CRUD)
Create, Read, Update, Delete
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import config


def load_data(filename='data.json'):
    """Загрузка данных из файла"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'users': {}}


def save_data(data, filename='data.json'):
    """Сохранение данных в файл"""
    Path('stats').mkdir(exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_data(user_id: int) -> Dict:
    """Получение всех данных пользователя"""
    data = load_data()
    user_key = str(user_id)
    
    if user_key not in data['users']:
        data['users'][user_key] = {
            'tasks': {'daily': {}, 'weekly': {}},
            'settings': {'planning_mode': 'weekly', 'reminders_enabled': True},
            'stats': {'tasks_added': 0, 'tasks_completed': 0, 'tasks_edited': 0, 'tasks_deleted': 0}
        }
        save_data(data)
    
    return data['users'][user_key]


def get_user_tasks(user_id: int, planning_mode: str = 'weekly') -> Dict:
    """Получение задач пользователя"""
    user_data = get_user_data(user_id)
    return user_data['tasks'].get(planning_mode, {})


def add_task(user_id: int, task_ Dict, planning_mode: str = 'weekly') -> Dict:
    """Добавление новой задачи"""
    data = load_data()
    user_key = str(user_id)
    user_data = data['users'].setdefault(user_key, {'tasks': {'daily': {}, 'weekly': {}}, 'stats': {}})
    
    target_dict = user_data['tasks'].setdefault(planning_mode, {})
    task_id = max(target_dict.keys(), default=0) + 1
    
    target_dict[task_id] = {
        'id': task_id,
        'title': task_data.get('title', 'Без названия'),
        'day': task_data.get('day', 'Monday'),
        'duration_hours': task_data.get('duration_hours', 1),
        'priority': task_data.get('priority', 'medium'),
        'completed': False,
        'created_at': datetime.now().isoformat(),
        'updated_at': None
    }
    
    user_data['stats']['tasks_added'] = user_data['stats'].get('tasks_added', 0) + 1
    data['users'][user_key] = user_data
    save_data(data)
    
    return {'success': True, 'task_id': task_id, 'message': f"✅ Задача #{task_id} добавлена"}


def get_task(user_id: int, task_id: int, planning_mode: str = 'weekly') -> Optional[Dict]:
    """Получение одной задачи по ID"""
    tasks = get_user_tasks(user_id, planning_mode)
    return tasks.get(task_id)


def edit_task(user_id: int, task_id: int, updates: Dict, planning_mode: str = 'weekly') -> Dict:
    """Редактирование существующей задачи"""
    data = load_data()
    user_key = str(user_id)
    
    if user_key not in data['users']:
        return {'success': False, 'error': 'Пользователь не найден'}
    
    tasks = data['users'][user_key]['tasks'].get(planning_mode, {})
    
    if task_id not in tasks:
        return {'success': False, 'error': f'Задача #{task_id} не найдена'}
    
    task = tasks[task_id]
    allowed_fields = ['title', 'day', 'duration_hours', 'priority', 'completed']
    
    for field, value in updates.items():
        if field in allowed_fields:
            task[field] = value
    
    task['updated_at'] = datetime.now().isoformat()
    data['users'][user_key]['stats']['tasks_edited'] = \
        data['users'][user_key]['stats'].get('tasks_edited', 0) + 1
    
    save_data(data)
    
    return {'success': True, 'task_id': task_id, 'message': f"✅ Задача #{task_id} обновлена", 'updated_task': task}


def delete_task(user_id: int, task_id: int, planning_mode: str = 'weekly') -> Dict:
    """Удаление задачи"""
    data = load_data()
    user_key = str(user_id)
    
    if user_key not in data['users']:
        return {'success': False, 'error': 'Пользователь не найден'}
    
    tasks = data['users'][user_key]['tasks'].get(planning_mode, {})
    
    if task_id not in tasks:
        return {'success': False, 'error': f'Задача #{task_id} не найдена'}
    
    deleted_task = tasks.pop(task_id)
    data['users'][user_key]['stats']['tasks_deleted'] = \
        data['users'][user_key]['stats'].get('tasks_deleted', 0) + 1
    
    save_data(data)
    
    return {'success': True, 'task_id': task_id, 'message': f"🗑️ Задача удалена", 'deleted_task': deleted_task}


def get_tasks_summary(user_id: int, planning_mode: str = 'weekly') -> str:
    """Текстовая сводка по задачам"""
    tasks = get_user_tasks(user_id, planning_mode)
    
    if not tasks:
        return "📭 Пока нет задач. Добавьте своё расписание!"
    
    days_ru = {
        'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда',
        'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота', 'Sunday': 'Воскресенье'
    }
    
    summary = f"📋 Ваши задачи ({'день' if planning_mode == 'daily' else 'неделя'}):\n\n"
    total_hours = 0
    
    for day in config.DAYS_EN:
        day_tasks = [t for t in tasks.values() if t.get('day') == day]
        if day_tasks:
            day_hours = sum(t.get('duration_hours', 0) for t in day_tasks)
            total_hours += day_hours
            summary += f"📅 {days_ru.get(day, day)}: {len(day_tasks)} задач ({day_hours}ч)\n"
            
            for task in day_tasks:
                priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task.get('priority'), '⚪')
                status = '✅' if task.get('completed') else '⏳'
                summary += f"   {status} {priority_icon} #{task['id']} {task['title']} ({task['duration_hours']}ч)\n"
            summary += "\n"
    
    summary += f"\n⏱️ Всего: {total_hours} часов"
    
    if total_hours > 40:
        summary += "\n\n⚠️ Нагрузка выше нормы!"
    
    return summary


def mark_task_completed(user_id: int, task_id: int, planning_mode: str = 'weekly') -> Dict:
    """Отметка задачи как выполненной"""
    result = edit_task(user_id, task_id, {'completed': True}, planning_mode)
    
    if result['success']:
        data = load_data()
        data['users'][str(user_id)]['stats']['tasks_completed'] = \
            data['users'][str(user_id)]['stats'].get('tasks_completed', 0) + 1
        save_data(data)
    
    return result


def clear_all_tasks(user_id: int, planning_mode: str = None) -> Dict:
    """Очистка всех задач"""
    data = load_data()
    user_key = str(user_id)
    
    if planning_mode == 'daily':
        data['users'][user_key]['tasks']['daily'] = {}
        message = "✅ Задачи на день очищены"
    elif planning_mode == 'weekly':
        data['users'][user_key]['tasks']['weekly'] = {}
        message = "✅ Задачи на неделю очищены"
    else:
        data['users'][user_key]['tasks'] = {'daily': {}, 'weekly': {}}
        message = "✅ Все задачи очищены"
    
    save_data(data)
    return {'success': True, 'message': message}