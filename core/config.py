"""config.py - every setting and constant lives here."""
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Read from .env locally or st.secrets on Streamlit Cloud (Audit-Guard pattern)
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or (st.secrets.get("GROQ_API_KEY") if hasattr(st, "secrets") else None)
GROQ_MODEL = os.getenv("GROQ_MODEL") or (st.secrets.get("GROQ_MODEL") if hasattr(st, "secrets") else "openai/gpt-oss-120b")

def _fix_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url

raw_db_url = os.getenv("DATABASE_URL") or (st.secrets.get("DATABASE_URL") if hasattr(st, "secrets") else "sqlite:///aura.db")
DATABASE_URL = _fix_db_url(raw_db_url.strip())

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
MISSED_DAYS_TRIGGER = 3

DISCLAIMER = (
    "Aura uses an AI model. Its plans, quizzes and answers can be wrong or out of date. "
    "It cannot browse the internet, so always check important facts in a trusted book, "
    "official documentation or with a teacher."
)
