"""profile.py - learner profile (also the first-time onboarding), privacy and account deletion."""
import re

import streamlit as st

from core import config
from core import database as db

_NICK_RE = re.compile(r"^[\w\- ]{2,20}$", re.UNICODE)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _pick(options, current):
    return options.index(current) if current in options else 0


def render(user: dict, onboarding: bool = False):
    uid = user["id"]
    if onboarding:
        st.title("Welcome to Aura")
        st.write("Tell me about you so every plan fits your real life. You can change this any time.")
    else:
        st.title("Profile and settings")

    with st.form("profile_form"):
        language = st.selectbox("Language for Aura's replies", config.LANGUAGES,
                                index=_pick(config.LANGUAGES, user["language"]))
        level = st.selectbox("Your level in what you want to learn", config.LEVELS,
                             index=_pick(config.LEVELS, user["level"]))
        minutes = st.number_input("Minutes you can study per day", min_value=10, max_value=480,
                                  step=5, value=int(user["daily_minutes"]))
        goal_type = st.selectbox("What kind of goal is it?", config.GOAL_TYPES,
                                 index=_pick(config.GOAL_TYPES, user["goal_type"]))
        deadline = st.date_input("Deadline (optional)", value=user["deadline"])
        intensity = st.select_slider("Intensity (more points, more effort)", options=config.INTENSITIES,
                                     value=user["intensity"] if user["intensity"] in config.INTENSITIES
                                     else "Balanced")
        st.markdown("**Privacy and reminders (all optional)**")
        nickname = st.text_input("Nickname (shown on the leaderboard)", value=user["nickname"],
                                 max_chars=20)
        on_board = st.checkbox("Show me on the leaderboard", value=bool(user["show_on_leaderboard"]))
        email = st.text_input("Email for reminders", value=user["email"])
        reminders = st.checkbox("Send me email reminders", value=bool(user["reminders_enabled"]))
        saved = st.form_submit_button("Save and continue" if onboarding else "Save settings")

    if saved:
        nickname, email = nickname.strip(), email.strip()
        if nickname and not _NICK_RE.match(nickname):
            st.error("Nickname: 2-20 letters, numbers, spaces, - or _.")
        elif on_board and not nickname:
            st.error("Choose a nickname to appear on the leaderboard.")
        elif (reminders or email) and not _EMAIL_RE.match(email):
            st.error("Please enter a valid email address.")
        elif reminders and not email:
            st.error("Enter your email to receive reminders.")
        else:
            db.update_user(uid, language=language, level=level, daily_minutes=int(minutes),
                           goal_type=goal_type, deadline=deadline, intensity=intensity,
                           nickname=nickname, show_on_leaderboard=1 if on_board else 0,
                           email=email, reminders_enabled=1 if reminders else 0, onboarded=1)
            if onboarding:
                st.rerun()
            st.success("Saved.")

    if onboarding:
        return
    st.divider()
    st.subheader("Delete my account")
    st.caption("This permanently erases your goals, chats, flashcards and notes.")
    sure = st.checkbox("I understand this cannot be undone")
    if st.button("Delete my account", disabled=not sure):
        db.delete_user(uid)
        st.session_state.clear()
        st.rerun()
