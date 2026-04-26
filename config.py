"""
🎵 Tempo Bot — Конфигурация
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# ===== ТОКЕН БОТА =====
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не найден в переменных окружения")

# ===== БАЗОВАЯ ДИРЕКТОРИЯ (работает на хостинге и локально) =====
BASE_DIR = Path(__file__).resolve().parent

# ===== ПУТИ К РЕСУРСАМ =====
RESOURCES_DIR = BASE_DIR / "resources"
AUDIO_DIR = RESOURCES_DIR / "audio"
IMAGES_DIR = RESOURCES_DIR / "images"
PDF_DIR = RESOURCES_DIR / "pdf"
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "data.json"

# ===== НАСТРОЙКИ =====
IDEAL_TASKS_PER_DAY = 5
MAX_TASKS_PER_DAY = 10

# ===== 5 ПРАКТИК (словарь — ТРЕБОВАНИЕ 2) =====
PRACTICES = {
    "p1": {
        "name": "🫁 Дыхание 4-7-8",
        "audio": "p1.mp3",
        "image": "p1.png",
        "desc": "Вдох 4, задержка 7, выдох 8"
    },
    "p2": {
        "name": "🌅 Мягкое пробуждение",
        "audio": "p2.mp3",
        "image": "p2.png",
        "desc": "Утренняя медитация"
    },
    "p3": {
        "name": "🌙 Спокойный сон",
        "audio": "p3.mp3",
        "image": "p3.png",
        "desc": "Подготовка ко сну"
    },
    "p4": {
        "name": "💆 Снять напряжение",
        "audio": "p4.mp3",
        "image": "p4.png",
        "desc": "Расслабление тела"
    },
    "p5": {
        "name": "🎯 Глубокий фокус",
        "audio": "p5.mp3",
        "image": "p5.png",
        "desc": "Концентрация внимания"
    },
}
