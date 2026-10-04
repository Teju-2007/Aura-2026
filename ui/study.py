"""study.py - flashcards with spaced repetition, quizzes, and reading lists."""
import json
from urllib.parse import quote_plus

import streamlit as st

from core import ai, spaced
from core import database as db
from ui.common import show_ai_error, today

SECTIONS = ["Review flashcards", "Make flashcards", "Quiz", "Reading list"]


# ---------------------------------------------------------------- callbacks
def _reveal(card_id: int):
    st.session_state["revealed_card"] = card_id


def _grade(uid: int, card_id: int, grade: str):
    card = db.get_card(uid, card_id)
    if card:
        now = today()
        ease, interval, reps, due = spaced.review_card(
            card["ease"], card["interval_days"], card["repetitions"], grade, now)
        db.save_card_review(uid, card_id, ease, interval, reps, due, grade, now)
    st.session_state.pop("revealed_card", None)


def _add_missed_to_flashcards(uid: int, task_id, cards):
    db.add_flashcards(uid, task_id, cards, today())
    st.session_state["quiz_result"]["added"] = True


# ----------------------------------------------------------------- sections
def _review(uid: int):
    due = db.get_due_cards(uid, today())
    if not due:
        st.success("No cards are due right now. Come back later, or make more flashcards.")
        return
    card = due[0]
    st.caption(f"{len(due)} card(s) due")
    with st.container(border=True):
        st.markdown(f"**Question:** {card['front']}")
        if st.session_state.get("revealed_card") == card["id"]:
            st.markdown(f"**Answer:** {card['back']}")
            st.write("How well did you remember?")
            cols = st.columns(4)
            for col, grade in zip(cols, spaced.GRADES):
                col.button(grade, key=f"grade_{grade}", on_click=_grade,
                           args=(uid, card["id"], grade), use_container_width=True)
        else:
            st.button("Show answer", on_click=_reveal, args=(card["id"],))


def _make_cards(user: dict, roadmap: dict, task: dict):
    st.write(f"Flashcards for this task so far: **{db.count_cards(user['id'], task['id'])}**")
    count = st.slider("How many new cards?", 4, 12, 8)
    if st.button("Generate flashcards"):
        try:
            with st.spinner("Writing flashcards..."):
                cards = ai.make_flashcards(task["description"], roadmap["title"], user, count)
            db.add_flashcards(user["id"], task["id"], cards, today())
            st.success(f"Added {len(cards)} flashcards. Review them in 'Review flashcards'.")
        except ai.AIError as exc:
            show_ai_error(exc)


def _quiz(user: dict, roadmap: dict, task: dict):
    uid = user["id"]
    if st.button("Create a new 5-question quiz"):
        try:
            with st.spinner("Writing quiz..."):
                questions = ai.make_quiz(task["description"], roadmap["title"], user, 5)
            st.session_state["quiz_counter"] = st.session_state.get("quiz_counter", 0) + 1
            st.session_state["quiz"] = {"id": st.session_state["quiz_counter"],
                                        "task_id": task["id"], "questions": questions}
            st.session_state.pop("quiz_result", None)
            st.rerun()
        except ai.AIError as exc:
            show_ai_error(exc)

    quiz = st.session_state.get("quiz")
    if quiz:
        with st.form(f"quiz_form_{quiz['id']}"):
            for i, q in enumerate(quiz["questions"]):
                st.radio(f"{i + 1}. {q['question']}", q["options"], index=None,
                         key=f"quiz_{quiz['id']}_q{i}")
            submitted = st.form_submit_button("Submit answers")
        if submitted:
            picks = [st.session_state.get(f"quiz_{quiz['id']}_q{i}")
                     for i in range(len(quiz["questions"]))]
            if any(p is None for p in picks):
                st.warning("Please answer every question.")
            else:
                details, score = [], 0
                for q, pick in zip(quiz["questions"], picks):
                    correct = q["options"][q["answer_index"]]
                    right = pick == correct
                    score += 1 if right else 0
                    details.append({**q, "picked": pick, "correct": correct, "right": right})
                db.save_quiz_result(uid, quiz["task_id"], score, len(details), today())
                st.session_state["quiz_result"] = {
                    "score": score, "total": len(details), "details": details,
                    "task_id": quiz["task_id"], "added": False}
                st.session_state.pop("quiz")
                st.rerun()

    result = st.session_state.get("quiz_result")
    if result:
        st.subheader(f"Score: {result['score']} / {result['total']}")
        missed = []
        for i, d in enumerate(result["details"], 1):
            icon = "Correct" if d["right"] else "Wrong"
            with st.expander(f"Question {i}: {icon}"):
                st.write(d["question"])
                st.write(f"Your answer: {d['picked']}")
                if not d["right"]:
                    st.write(f"Correct answer: **{d['correct']}**")
                    missed.append({"front": d["question"],
                                   "back": f"{d['correct']}. {d['explanation']}".strip()})
                if d["explanation"]:
                    st.caption(d["explanation"])
        if missed and not result["added"]:
            st.button("Add my missed questions to flashcards", on_click=_add_missed_to_flashcards,
                      args=(uid, result["task_id"], missed))
        elif result["added"]:
            st.success("Missed questions were added to your flashcards.")


def _reading(user: dict, roadmap: dict, task: dict):
    saved = []
    if task["resources"]:
        try:
            saved = json.loads(task["resources"])
        except json.JSONDecodeError:
            saved = []
    if st.button("Suggest reading list" if not saved else "Suggest a new reading list"):
        try:
            with st.spinner("Thinking of good reading..."):
                saved = ai.suggest_resources(task["description"], roadmap["title"], user)
            db.save_task_resources(user["id"], task["id"], json.dumps(saved, ensure_ascii=False))
        except ai.AIError as exc:
            show_ai_error(exc)
    for item in saved:
        link = "https://www.google.com/search?q=" + quote_plus(item["search_query"])
        st.markdown(f"**{item['title']}** ({item['kind']})  \n{item['why']}  \n[Search for it]({link})")
    if saved:
        st.caption("Titles come from an AI that cannot browse the web. Confirm each one exists "
                   "before you rely on it.")


# --------------------------------------------------------------------- page
def render(user: dict):
    uid = user["id"]
    st.title("Study")
    section = st.radio("Section", SECTIONS, horizontal=True, key="study_section",
                       label_visibility="collapsed")

    if section == SECTIONS[0]:
        _review(uid)
        return

    roadmap = db.get_active_roadmap(uid)
    task_rows = db.get_tasks(uid, roadmap["id"]) if roadmap else []
    if not task_rows:
        st.info("Build a goal on the Architect page first. Then you can study each task here.")
        return
    by_id = {t["id"]: t for t in task_rows}
    chosen = st.selectbox("Choose a task", list(by_id), format_func=lambda i: by_id[i]["description"])
    task = by_id[chosen]

    if section == SECTIONS[1]:
        _make_cards(user, roadmap, task)
    elif section == SECTIONS[2]:
        _quiz(user, roadmap, task)
    else:
        _reading(user, roadmap, task)
