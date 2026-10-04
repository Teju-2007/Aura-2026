"""config.py - every setting and constant lives here.

Other files import from this file, so you change a value in ONE place only.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # reads the ".env" file (if it exists) into environment variables

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()


def _fix_db_url(url: str) -> str:
    """Hosting sites often give 'postgres://...'; SQLAlchemy wants a driver name."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _fix_db_url(os.getenv("DATABASE_URL", "sqlite:///aura.db").strip())

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip() or SMTP_USER

LANGUAGES = [
    "English", "Hindi", "Telugu", "Tamil", "Bengali", "Marathi", "Urdu",
    "Spanish", "French", "German", "Portuguese", "Arabic", "Chinese",
    "Japanese", "Indonesian", "Swahili",
]
LEVELS = ["Beginner", "Intermediate", "Advanced"]
GOAL_TYPES = [
    "Exam / school or college",
    "Career switch",
    "Job skill upgrade",
    "Hobby / curiosity",
]
INTENSITIES = ["Chill", "Balanced", "Beast Mode"]
INTENSITY_POINTS = {"Chill": 5, "Balanced": 10, "Beast Mode": 20}
MOODS = ["Drained", "Low", "Neutral", "High", "Limitless"]

MAX_UPLOAD_MB = 5
MISSED_DAYS_TRIGGER = 3  # after this many days without a log, offer a lighter plan

DISCLAIMER = (
    "Aura uses an AI model. Its plans, quizzes and answers can be wrong or out of date. "
    "It cannot browse the internet, so always check important facts in a trusted book, "
    "official documentation or with a teacher."
)
