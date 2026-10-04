"""common.py - tiny helpers shared by the screens."""
from datetime import date

import streamlit as st


def today() -> date:
    return date.today()


def current_mood() -> str:
    return st.session_state.get("mood", "Neutral")


def show_ai_error(exc: Exception):
    st.error(str(exc))
