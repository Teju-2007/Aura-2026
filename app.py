"""app.py - the front door. Run with:  streamlit run app.py

It only decides WHAT to show (login, onboarding, or a page). The real work lives in
core/ (logic and data) and ui/ (screens).
"""
import streamlit as st

from core import config, database as db
from ui import architect, coach, leaderboard, notes, profile, progress, sidebar, study

st.set_page_config(page_title="Aura 2026", page_icon=":material/rocket_launch:", layout="wide")


@st.cache_resource
def _setup_database() -> bool:
    db.init_db()
    return True


_setup_database()

ROUTES = {
    "Architect": architect.render,
    "Study": study.render,
    "My Notes": notes.render,
    "Coach & History": coach.render,
    "Progress": progress.render,
    "Leaderboard": leaderboard.render,
    "Profile": profile.render,
}

user = db.get_user(st.session_state["user_id"]) if st.session_state.get("user_id") else None

if user is None:
    st.session_state.pop("user_id", None)
    sidebar.render_auth()
    st.title("Aura 2026")
    st.write("Your AI learning coach: plan, learn, test and adapt. Log in from the sidebar to begin.")
    st.caption(config.DISCLAIMER)
else:
    page = sidebar.render_nav(user)
    if not user["onboarded"]:
        profile.render(user, onboarding=True)
    else:
        ROUTES[page](user)
    st.divider()
    st.caption(config.DISCLAIMER)

st.caption("Built by Tejaveni Chillapalli | Aspiring ML Engineer")
