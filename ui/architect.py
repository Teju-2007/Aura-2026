"""architect.py - the chat where Aura interviews you and builds your roadmap."""
import streamlit as st

from core import ai, database as db
from ui.common import current_mood, show_ai_error

GREETING = (
    "Hi! I am Aura. Tell me what you want to learn or achieve, and why it matters to you. "
    "I already know your level and daily time from your profile, so I will only ask what I "
    "still need."
)


def render(user: dict):
    uid = user["id"]
    st.title("Architect: define your vision")

    if st.button("Start a new goal (clears this chat)"):
        db.clear_messages(uid)
        st.rerun()

    history = db.get_messages(uid, limit=50)
    if not history:
        with st.chat_message("assistant"):
            st.markdown(GREETING)
    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Tell Aura your goal...")
    if not prompt:
        return

    db.add_message(uid, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Aura is thinking..."):
                result = ai.architect_reply(db.get_messages(uid, limit=20), user, current_mood())
        except ai.AIError as exc:
            show_ai_error(exc)
            return

        text = result["text"] or "Here is your roadmap."
        st.markdown(text)
        db.add_message(uid, "assistant", text)  # the JSON block is never saved in the chat

        if result["tasks"]:
            db.save_roadmap(uid, result["title"] or "My learning goal", text, result["tasks"])
            st.success("Roadmap finalized! Your tasks are on the Progress page.")
        elif result["json_error"]:
            st.warning("I could not read the task list. Reply 'please send the task list again'.")
