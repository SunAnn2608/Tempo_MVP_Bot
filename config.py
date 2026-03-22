import os
from dotenv import load_dotenv

load_dotenv()

# ===== ТОКЕНЫ =====
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не найден в .env")

# ===== ПУТИ =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUDIO_DIR = os.path.join(BASE_DIR, "resources/audio")
IMAGES_DIR = os.path.join(BASE_DIR, "resources/images")
PDF_DIR = os.path.join(BASE_DIR, "resources/pdf")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# ===== ЛОГИКА НАГРУЗКИ =====
IDEAL_TASKS_PER_DAY = 5
MAX_TASKS_PER_DAY = 10

# ===== AI =====
AI_MODEL = "gpt-4o-mini"

# ===== ПРАКТИКИ =====
PRACTICES = {
    "p1": {
        "name": "🫁 Дыхание 4-7-8",
        "audio": "p1.ogg",
        "image": "p1.png"
    },
    "p2": {
        "name": "🌅 Мягкое пробуждение",
        "audio": "p2.ogg",
        "image": "p2.png"
    },
    "p3": {
        "name": "🌙 Спокойный сон",
        "audio": "p3.ogg",
        "image": "p3.png"
    },
    "p4": {
        "name": "💆 Снять напряжение",
        "audio": "p4.ogg",
        "image": "p4.png"
    },
    "p5": {
        "name": "🎯 Глубокий фокус",
        "audio": "p5.ogg",
        "image": "p5.png"
    }
}