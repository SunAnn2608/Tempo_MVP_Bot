"""
🤖 Tempo Bot — AI-анализ расписания
Интеграция с OpenAI API
"""

import os
import json
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY != 'YOUR_OPENAI_API_KEY_HERE' else None


def analyze_schedule_text(text: str, planning_mode: str = 'weekly') -> dict:
    """Анализ текстового расписания"""
    if client is None:
        return {
            'error': 'API ключ не настроен',
            'risk_level': 'unknown',
            'warnings': [],
            'recommendations': ['Настройте OpenAI API ключ']
        }
    
    if not text or len(text.strip()) < 10:
        return {
            'error': 'Слишком мало данных',
            'risk_level': 'unknown',
            'warnings': [],
            'recommendations': []
        }
    
    try:
        system_prompt = {
            'weekly': """Ты — эксперт по балансу работы и отдыха. Проанализируй недельное расписание.
            Верни JSON: risk_level (low/medium/high/critical), total_hours, warnings[], recommendations[]""",
            'daily': """Ты — эксперт по продуктивности. Проанализируй расписание на день.
            Верни JSON: risk_level, total_hours, warnings[], recommendations[]"""
        }
        
        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt.get(planning_mode, system_prompt['weekly'])},
                {"role": "user", "content": f"Проанализируй расписание ({planning_mode}):\n\n{text}"}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content
        start = content.find('{')
        end = content.rfind('}') + 1
        
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        else:
            return {'analysis': content, 'risk_level': 'medium', 'warnings': [], 'recommendations': []}
    
    except Exception as e:
        return {'error': str(e), 'risk_level': 'unknown', 'warnings': [], 'recommendations': []}


def extract_tasks_from_text(text: str, planning_mode: str = 'weekly') -> list:
    """Извлечение задач из текста"""
    tasks = []
    lines = text.split('\n')
    days_ru = {
        'понедельник': 'Monday', 'вторник': 'Tuesday', 'среда': 'Wednesday',
        'четверг': 'Thursday', 'пятница': 'Friday', 'суббота': 'Saturday', 'воскресенье': 'Sunday'
    }
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        for day_ru, day_en in days_ru.items():
            if day_ru in line.lower() or day_en.lower() in line.lower():
                task = {
                    'day': day_en,
                    'title': line.split(':')[0] if ':' in line else line,
                    'duration_hours': 1,
                    'priority': 'medium'
                }
                
                import re
                hours_match = re.search(r'(\d+)[\s]*(ч|час|hour|h)', line, re.IGNORECASE)
                if hours_match:
                    task['duration_hours'] = int(hours_match.group(1))
                
                tasks.append(task)
                break
    
    return tasks


def get_quick_tip() -> str:
    """Быстрый совет от AI"""
    if client is None:
        return "🎵 Заботьтесь о балансе работы и отдыха!"
    
    try:
        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": "Дай короткий совет по предотвращению выгорания (1-2 предложения)"},
                {"role": "user", "content": "Совет на сегодня"}
            ],
            max_tokens=100
        )
        return f"💡 {response.choices[0].message.content}"
    except:
        return "🎵 Сделайте перерыв прямо сейчас!"