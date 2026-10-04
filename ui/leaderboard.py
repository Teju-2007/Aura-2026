"""leaderboard.py - opt-in ranking by nickname (real usernames are never shown)."""
import pandas as pd
import streamlit as st

from core import database as db

_ICONS = {1: "1st", 2: "2nd", 3: "3rd"}


def render(user: dict):
    st.title("Leaderboard")
    st.write("Only learners who opted in appear here, under their nickname.")
    board = db.get_leaderboard(10)
    if board:
        frame = pd.DataFrame(
            [(_ICONS.get(i, f"{i}th"), name, pts) for i, (name, pts) in enumerate(board, 1)],
            columns=["Rank", "Nickname", "Aura points"])
        st.dataframe(frame, hide_index=True, use_container_width=True)
        st.bar_chart(frame.head(5).set_index("Nickname")["Aura points"])
    else:
        st.info("Nobody has joined the leaderboard yet. Be the first!")

    st.info(f"Your points: **{user['aura_points']}**")
    if not user["show_on_leaderboard"]:
        st.caption("You are hidden. Join from Profile by choosing a nickname and ticking the box.")
