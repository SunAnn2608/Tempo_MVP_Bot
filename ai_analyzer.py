"""
🤖 Tempo Bot — AI-анализ расписания

Работает в двух режимах:
1. С API-ключом OpenAI — реальный анализ через GPT
2. Без ключа — эмуляция анализа по правилам (демо-режим)
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_ENABLED = bool(OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE")

if AI_ENABLED:
    try:
        from openai import OpenAI
        ai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI клиент инициализирован")
    except ImportError:
        logger.warning("⚠️ openai пакет не установлен — работа в демо-режиме")
        AI_ENABLED = False
        ai_client = None
else:
    logger.info("ℹ️ OPENAI_API_KEY не настроен — работа в демо-режиме")
    ai_client = None


DEMO_KEYWORDS = {
    "overload": ["много", "перегрузка", "устал", "не успеваю", "стресс", "выгор"],
    "balanced": ["баланс", "спокойно", "нормально", "всё под контролем"],
    "morning_person": ["утро", "рано", "проснулся", "бодр"],
    "night_owl": ["ночь", "поздно", "сова", "вечер"]
}

DEMO_RECOMMENDATIONS = {
    "overload": [
        "🔴 Обнаружена перегрузка. Попробуйте перенести 1-2 задачи на завтра",
        "💡 Добавьте 15-минутные перерывы между задачами",
        "🎧 Попробуйте практику «Снять напряжение» после работы"
    ],
    "balanced": [
        "🟢 Отличный баланс! Продолжайте в том же духе",
        "✨ Не забывайте про микро-паузы каждые 2 часа",
        "🎵 5 минут отдыха — и вы в ресурсе"
    ],
    "default": [
        "💡 Попробуйте планировать не более 5 задач в день",
        "☕ Не забывайте про перерывы — они повышают продуктивность",
        "🌙 Завершайте рабочий день практикой «Спокойный сон»"
    ]
}


def parse_schedule_text(text: str) -> List[Dict]:
    tasks = []
    lines = text.strip().split("\n")
    
    days_ru = {
        "понедельник": "Monday", "вторник": "Tuesday", "среда": "Wednesday",
        "четверг": "Thursday", "пятница": "Friday", "суббота": "Saturday", "воскресенье": "Sunday"
    }
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        day_found = None
        for day_ru, day_en in days_ru.items():
            if day_ru in line.lower():
                day_found = day_en
                break
        
        if not day_found:
            continue
        
        task = {"day": day_found, "title": line, "duration_hours": 1, "priority": "medium"}
        
        hours_match = re.search(r'(\d+)[\s]*(ч|час|часов|hour|h)', line, re.IGNORECASE)
        if hours_match:
            task["duration_hours"] = int(hours_match.group(1))
        
        if "важно" in line.lower() or "срочно" in line.lower():
            task["priority"] = "high"
        elif "можно потом" in line.lower() or "не срочно" in line.lower():
            task["priority"] = "low"
        
        tasks.append(task)
    
    return tasks


def calculate_load(tasks: List[Dict]) -> Dict[str, float]:
    load = {}
    
    for task in tasks:
        day = task.get("day", "Unknown")
        hours = task.get("duration_hours", 1)
        load[day] = load.get(day, 0) + hours
    
    return load


def analyze_risk_demo(tasks: List[Dict]) -> Dict:
    load = calculate_load(tasks)
    total_hours = sum(load.values())
    
    if total_hours > 50:
        risk_level = "critical"
        risk_emoji = "🔴"
    elif total_hours > 40:
        risk_level = "high"
        risk_emoji = "🟠"
    elif total_hours > 30:
        risk_level = "medium"
        risk_emoji = "🟡"
    else:
        risk_level = "low"
        risk_emoji = "🟢"
    
    warnings = []
    for day, hours in load.items():
        if hours > 10:
            warnings.append(f"⚠️ {day}: {hours}ч — высокая нагрузка")
    
    text = " ".join(t.get("title", "") for t in tasks).lower()
    recommendations = DEMO_RECOMMENDATIONS["default"].copy()
    
    for keyword_type, keywords in DEMO_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            if keyword_type == "overload":
                recommendations = DEMO_RECOMMENDATIONS["overload"]
            elif keyword_type == "balanced":
                recommendations = DEMO_RECOMMENDATIONS["balanced"]
            break
    
    return {
        "risk_level": risk_level,
        "risk_emoji": risk_emoji,
        "total_hours": total_hours,
        "load_by_day": load,
        "warnings": warnings,
        "recommendations": recommendations,
        "mode": "demo"
    }


def analyze_risk_ai(text: str) -> Optional[Dict]:
    if not AI_ENABLED or ai_client is None:
        return None
    
    try:
        response = ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """Ты — эксперт по балансу работы и отдыха.
Проанализируй расписание пользователя и оцени риск выгорания.
Верни ответ ТОЛЬКО в формате JSON с полями:
- risk_level: "low", "medium", "high" или "critical"
- total_hours: число
- warnings: список строк с предупреждениями
- recommendations: список строк с рекомендациями
- load_by_day: объект с нагрузкой по дням"""
                },
                {
                    "role": "user",
                    "content": f"Проанализируй моё расписание:\n\n{text}"
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        
        start = content.find("{")
        end = content.rfind("}") + 1
        
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
            result["mode"] = "ai"
            return result
        
        logger.warning("Не удалось распарсить JSON из ответа AI")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка AI-анализа: {e}")
        return None


def analyze_schedule(text: str) -> Dict:
    if not text or len(text.strip()) < 10:
        return {
            "error": "Слишком мало данных для анализа",
            "risk_level": "unknown",
            "recommendations": ["Добавьте больше информации о вашем расписании"]
        }
    
    if AI_ENABLED:
        result = analyze_risk_ai(text)
        if result:
            logger.info("✅ AI-анализ выполнен")
            return result
    
    logger.info("🔄 Демо-анализ (режим без API)")
    tasks = parse_schedule_text(text)
    
    if not tasks:
        return {
            "error": "Не удалось распознать задачи. Попробуйте формат: 'Понедельник: Работа 8ч'",
            "risk_level": "unknown",
            "recommendations": ["Используйте формат: День: Задача (часы)"]
        }
    
    return analyze_risk_demo(tasks)


def format_analysis_result(result: Dict) -> str:
    if "error" in result:
        return f"⚠️ {result['error']}\n\n💡 {result.get('recommendations', ['Попробуйте ещё раз'])[0]}"
    
    risk_emoji = result.get("risk_emoji", "⚪")
    risk_level = result.get("risk_level", "unknown").upper()
    mode = result.get("mode", "demo")
    
    text = f"📊 Анализ расписания ({mode})\n\n"
    text += f"Риск выгорания: {risk_emoji} {risk_level}\n"
    text += f"⏱️ Всего часов: {result.get('total_hours', 'N/A')}\n\n"
    
    if result.get("warnings"):
        text += "⚠️ Предупреждения:\n" + "\n".join(f"• {w}" for w in result["warnings"][:3]) + "\n\n"
    
    if result.get("recommendations"):
        text += "💡 Рекомендации:\n" + "\n".join(f"• {r}" for r in result["recommendations"][:3])
    
    text += f"\n\n{config.USP}"
    
    return text


def save_analysis_history(user_id: int, text: str, result: Dict):
    from task_manager import load_data, save_data
    import datetime
    
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {}
    
    if "analyses" not in data["users"][user_id_str]:
        data["users"][user_id_str]["analyses"] = []
    
    analysis_record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "input_preview": text[:100] + "..." if len(text) > 100 else text,
        "risk_level": result.get("risk_level"),
        "mode": result.get("mode", "demo")
    }
    
    data["users"][user_id_str]["analyses"].append(analysis_record)
    
    if len(data["users"][user_id_str]["analyses"]) > 10:
        data["users"][user_id_str]["analyses"] = data["users"][user_id_str]["analyses"][-10:]
    
    save_data(data)
    logger.info(f"Анализ сохранён для пользователя {user_id}")
