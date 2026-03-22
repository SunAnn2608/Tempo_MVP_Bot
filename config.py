import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не найден")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUDIO_DIR = os.path.join(BASE_DIR, "resources/audio")
IMAGES_DIR = os.path.join(BASE_DIR, "resources/images")
PDF_DIR = os.path.join(BASE_DIR, "resources/pdf")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

IDEAL_TASKS_PER_DAY = 5
MAX_TASKS_PER_DAY = 10

AI_MODEL = "gpt-4o-mini"

DAYS_EN = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]

PRACTICES = {
    "p1": {"name": "🫁 Дыхание 4-7-8", "audio": "p1.mp3", "image": "p1.png"},
    "p2": {"name": "🌅 Мягкое пробуждение", "audio": "p2.mp3", "image": "p2.png"},
    "p3": {"name": "🌙 Спокойный сон", "audio": "p3.mp3", "image": "p3.png"},
    "p4": {"name": "💆 Снять напряжение", "audio": "p4.mp3", "image": "p4.png"},
    "p5": {"name": "🎯 Глубокий фокус", "audio": "p5.mp3", "image": "p5.png"},
}