"""sidebar.py - login/sign-up box, page menu, energy check-in and logout."""
import streamlit as st

from core import auth, config

PAGES = ["Architect", "Study", "My Notes", "Coach & History", "Progress", "Leaderboard", "Profile"]


def render_auth():
    """Show the login / sign-up forms. Returns nothing; sets session_state on success."""
    st.sidebar.title("Aura 2026")
    mode = st.sidebar.radio("Account", ["Login", "Sign Up"], horizontal=True)
    if mode == "Login":
        with st.sidebar.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            user = auth.login(username, password)
            if user:
                st.session_state["user_id"] = user["id"]
                st.rerun()
            else:
                st.sidebar.error("Invalid username or password.")
    else:
        with st.sidebar.form("signup_form"):
            username = st.text_input("Choose a username")
            password = st.text_input("Choose a password (8+ characters)", type="password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            user_id, message = auth.register(username, password)
            if user_id:
                st.session_state["user_id"] = user_id
                st.rerun()
            else:
                st.sidebar.error(message)


def render_nav(user: dict) -> str:
    """Show the menu for a logged-in user and return the chosen page name."""
    st.sidebar.title("Aura 2026")
    st.sidebar.write(f"Logged in as **{user['username']}**")
    st.sidebar.metric("Aura Points", user["aura_points"])
    page = st.sidebar.radio("Go to", PAGES, key="page")
    st.sidebar.divider()
    st.sidebar.subheader("Energy check-in")
    st.sidebar.select_slider("How are you feeling today?", options=config.MOODS,
                             value="Neutral", key="mood")
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    return page
