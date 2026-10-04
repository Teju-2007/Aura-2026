"""coach.py - ask the coach questions about your goal, and browse/activate old roadmaps."""
import streamlit as st

from core import ai, database as db
from ui.common import show_ai_error


def render(user: dict):
    uid = user["id"]
    st.title("Coach and history")

    active = db.get_active_roadmap(uid)
    if active:
        st.info(f"Currently focused on: **{active['title']}**")
        with st.container(border=True):
            st.subheader("Doubt resolver")
            with st.form("coach_form"):
                question = st.text_area(
                    "Stuck? Ask for an explanation:",
                    placeholder="How does backpropagation work?")
                asked = st.form_submit_button("Get guidance")
            if asked:
                if not question.strip():
                    st.warning("Please type a question first.")
                else:
                    try:
                        with st.spinner("Thinking..."):
                            answer = ai.coach_answer(active["title"], active["content"],
                                                     question.strip(), user)
                        st.markdown(answer)
                    except ai.AIError as exc:
                        show_ai_error(exc)
    else:
        st.info("No active goal yet. Build one on the Architect page.")

    st.divider()
    st.subheader("Goal history")
    history = db.get_roadmaps(uid)
    if not history:
        st.info("No roadmaps saved yet.")
    for roadmap in history:
        created = roadmap["created_at"].strftime("%Y-%m-%d") if roadmap["created_at"] else ""
        left, right = st.columns([4, 1])
        with left:
            with st.expander(f"{created} | {roadmap['title']}"):
                st.markdown(roadmap["content"])
        with right:
            if roadmap["is_active"]:
                st.success("Active")
            else:
                st.button("Activate", key=f"activate_{roadmap['id']}",
                          on_click=db.set_active_roadmap, args=(uid, roadmap["id"]))
