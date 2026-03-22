import json
import re

from openai import OpenAI
import config


# ===== КЛИЕНТ =====

client = None
if config.OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
    except:
        client = None


# ===== АНАЛИЗ =====

def analyze_schedule_text(text: str, planning_mode: str = 'weekly') -> dict:
    if not text or len(text.strip()) < 5:
        return {
            'risk_level': 'unknown',
            'warnings': [],
            'recommendations': []
        }

    if client is None:
        return simple_analysis(text)

    try:
        system_prompt = (
            "Ты анализируешь расписание и оцениваешь нагрузку.\n"
            "Ответь ТОЛЬКО JSON:\n"
            "{risk_level: low/medium/high/critical, warnings: [], recommendations: []}"
        )

        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.5,
            max_tokens=500
        )

        content = response.choices[0].message.content
        return safe_json_parse(content)

    except:
        return simple_analysis(text)


# ===== JSON =====

def safe_json_parse(text: str) -> dict:
    try:
        start = text.find('{')
        end = text.rfind('}') + 1

        if start == -1 or end == 0:
            raise ValueError

        return json.loads(text[start:end])

    except:
        return {
            'risk_level': 'medium',
            'warnings': [],
            'recommendations': []
        }


# ===== FALLBACK =====

def simple_analysis(text: str) -> dict:
    numbers = re.findall(r'\d+', text)
    load = len(numbers)

    if load > 15:
        risk = 'high'
    elif load > 8:
        risk = 'medium'
    else:
        risk = 'low'

    return {
        'risk_level': risk,
        'warnings': ['Высокая нагрузка'] if risk != 'low' else [],
        'recommendations': ['Снизь количество задач']
    }


# ===== ИЗВЛЕЧЕНИЕ ЗАДАЧ =====

def extract_tasks_from_text(text: str, planning_mode: str = 'weekly') -> list:
    tasks = []

    days = {
        'понедельник': 'Monday',
        'вторник': 'Tuesday',
        'среда': 'Wednesday',
        'четверг': 'Thursday',
        'пятница': 'Friday',
        'суббота': 'Saturday',
        'воскресенье': 'Sunday'
    }

    for line in text.split('\n'):
        raw_line = line.strip()
        line = raw_line.lower()

        if not line:
            continue

        for ru, en in days.items():
            if ru in line or en.lower() in line:
                task = {
                    'title': raw_line[:40],
                    'day': en,
                    'duration_hours': 1,
                    'priority': 'medium'
                }

                match = re.search(r'(\d+)', line)
                if match:
                    task['duration_hours'] = int(match.group(1))

                tasks.append(task)
                break

    return tasks


# ===== ПЕРЕРАСПРЕДЕЛЕНИЕ =====

def redistribute_tasks(tasks: list) -> list:
    """
    Простое перераспределение задач по дням
    """
    days = config.DAYS_EN
    result = []

    day_index = 0
    daily_count = {}

    for task in tasks:
        assigned = False

        for _ in range(len(days)):
            day = days[day_index % len(days)]

            count = daily_count.get(day, 0)

            if count < config.MAX_TASKS_PER_DAY:
                new_task = task.copy()
                new_task['day'] = day

                result.append(new_task)

                daily_count[day] = count + 1
                assigned = True
                break

            day_index += 1

        if not assigned:
            result.append(task)

    return result


# ===== AI СОВЕТ =====

def ai_workload_advice(summary: str) -> str:
    if client is None:
        return "💡 Попробуй снизить нагрузку и оставить 5 задач в день"

    try:
        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": "Ты коуч по предотвращению выгорания"},
                {"role": "user", "content": f"Проанализируй нагрузку:\n{summary}"}
            ],
            max_tokens=150
        )

        return f"💡 {response.choices[0].message.content}"

    except:
        return "💡 Попробуй распределить задачи равномерно"


# ===== БЫСТРЫЙ СОВЕТ =====

def get_quick_tip() -> str:
    if client is None:
        return "💡 Сделай паузу и подыши"

    try:
        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": "Дай короткий совет по продуктивности"},
                {"role": "user", "content": "Совет"}
            ],
            max_tokens=50
        )

        return f"💡 {response.choices[0].message.content}"

    except:
        return "💡 Отдохни пару минут"