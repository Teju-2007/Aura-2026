"""config.py - every setting and constant lives here.

Other files import from this file, so you change a value in ONE place only.
"""
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # reads local ".env" file if present


def _get_secret(key: str, default: str = "") -> str:
    """Safely retrieves a configuration value from Streamlit Secrets first,
    falling back to environment variables (.env), and finally to a default value.
    """
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            val = st.secrets[key]
            if val is not None:
                return str(val)
    except Exception:
        pass
    val = os.getenv(key)
    if val is not None:
        return str(val)
    return default


# --- API KEYS & MODELS ---
GROQ_API_KEY = _get_secret("GROQ_API_KEY").strip()
GROQ_MODEL = _get_secret("GROQ_MODEL", "openai/gpt-oss-120b").strip()


# --- DATABASE CONFIGURATION ---
def _fix_db_url(url: str) -> str:
    """Hosting sites often give 'postgres://...'; SQLAlchemy wants a driver name."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


raw_db_url = _get_secret("DATABASE_URL", "sqlite:///aura.db").strip()
DATABASE_URL = _fix_db_url(raw_db_url)


# --- SMTP / EMAIL CONFIGURATION ---
SMTP_HOST = _get_secret("SMTP_HOST", "").strip()
SMTP_PORT = int(_get_secret("SMTP_PORT", "587").strip() or 587)
SMTP_USER = _get_secret("SMTP_USER", "").strip()
SMTP_PASSWORD = _get_secret("SMTP_PASSWORD", "").strip()
SMTP_FROM = _get_secret("SMTP_FROM", "").strip() or SMTP_USER


# --- APPLICATION CONSTANTS ---
LANGUAGES = [
    "English",
    "Hindi",
    "Telugu",
    "Tamil",
    "Bengali",
    "Marathi",
    "Urdu",
    "Spanish",
    "French",
    "German",
    "Portuguese",
    "Arabic",
    "Chinese",
    "Japanese",
    "Indonesian",
    "Swahili",
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
