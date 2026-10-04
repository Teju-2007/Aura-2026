"""test_app.py - drives the real Streamlit screens with a fake AI (no internet, no API key)."""
import json
import os
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import update
from streamlit.testing.v1 import AppTest

from core import ai, auth
from core import database as db

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
FINAL = ('Here is your blueprint.\n---JSON---\n{"title": "Learn Python", '
         '"tasks": ["Read chapter 1", "Do 5 exercises", "Build a tiny script"]}\n---END---')


def fake_complete(messages, temperature=0.7, json_mode=False, max_tokens=2500):
    system = messages[0]["content"]
    if "warm, practical learning coach" in system:
        last = messages[-1]["content"]
        return FINAL if "ready" in last else "What do you already know about Python?"
    if "flashcards" in system:
        return json.dumps({"cards": [{"front": f"Q{i}", "back": f"A{i}"} for i in range(4)]})
    if "multiple-choice" in system:
        return json.dumps({"questions": [
            {"question": f"Question {i}?", "options": ["w", "x", "y", "z"],
             "answer_index": 1, "explanation": "because x"} for i in range(3)]})
    if "READING-FIRST" in system:
        return json.dumps({"resources": [{"title": "Python Crash Course", "kind": "book",
                                          "why": "Good start", "search_query": "Python Crash Course"}]})
    if "shrink study tasks" in system:
        return json.dumps({"tasks": ["Read one page", "Write one line of code"]})
    return "A helpful answer."


@pytest.fixture(autouse=True)
def fake_ai(monkeypatch):
    monkeypatch.setattr(ai, "_complete", fake_complete)


def new_app(onboarded=True, name="learner"):
    uid, _ = auth.register(name, "password123")
    if onboarded:
        db.update_user(uid, onboarded=1)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["user_id"] = uid
    at.run()
    assert not at.exception
    return at, uid


def quiz_radios(at):
    """Only the quiz question radios (not the sidebar menu or the section picker)."""
    return [r for r in at.radio if r.key and r.key.startswith("quiz_")]


def go(at, page):
    at.sidebar.radio(key="page").set_value(page).run()
    assert not at.exception, at.exception
    return at


def test_signup_and_onboarding():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Sign Up").run()
    at.sidebar.text_input[0].input("brand_new")
    at.sidebar.text_input[1].input("password123")
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert "Welcome to Aura" in at.title[0].value  # onboarding first
    at.selectbox[0].select("Telugu")
    at.number_input[0].set_value(45)
    next(b for b in at.button if "Save and continue" in b.label).click().run()
    assert not at.exception
    user = db.get_user_by_name("brand_new")
    assert user["onboarded"] == 1 and user["language"] == "Telugu" and user["daily_minutes"] == 45
    assert at.title[0].value.startswith("Architect")


def test_bad_login_and_logout():
    auth.register("someone", "password123")
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.text_input[0].input("someone")
    at.sidebar.text_input[1].input("wrong-password")
    at.sidebar.button[0].click().run()
    assert at.sidebar.error and not at.exception
    at, _ = new_app(name="other_user")
    next(b for b in at.sidebar.button if b.label == "Logout").click().run()
    assert not at.exception and at.title[0].value == "Aura 2026"


def test_architect_chat_roadmap_and_history():
    at, uid = new_app()
    at.chat_input[0].set_value("I want to learn Python").run()
    assert not at.exception and db.get_active_roadmap(uid) is None
    at.chat_input[0].set_value("I am ready").run()
    assert not at.exception
    roadmap = db.get_active_roadmap(uid)
    assert roadmap["title"] == "Learn Python"
    assert len(db.get_tasks(uid, roadmap["id"])) == 3
    saved = " ".join(m["content"] for m in db.get_messages(uid))
    assert "---JSON---" not in saved  # raw JSON never reaches the chat history
    # a page refresh (new AppTest, same user) still shows the conversation
    at2 = AppTest.from_file(APP, default_timeout=30)
    at2.session_state["user_id"] = uid
    at2.run()
    assert any("blueprint" in m.value for m in at2.markdown)


def test_ai_failure_shows_message_not_crash(monkeypatch):
    def boom(*a, **k):
        raise ai.AIError("The AI is busy (rate limit reached). Please wait a minute and try again.")
    monkeypatch.setattr(ai, "_complete", boom)
    at, _ = new_app()
    at.chat_input[0].set_value("hello").run()
    assert not at.exception and any("rate limit" in e.value for e in at.error)


def test_progress_tasks_and_one_log_per_day():
    at, uid = new_app()
    db.save_roadmap(uid, "Goal", "text", ["Task A", "Task B"])
    go(at, "Progress")
    at.checkbox[0].check().run()
    assert not at.exception
    assert db.get_tasks(uid, db.get_active_roadmap(uid)["id"])[0]["is_done"] == 1
    next(b for b in at.button if b.label == "Log today's success").click().run()
    assert not at.exception and db.get_user(uid)["aura_points"] == 10
    assert any(b.label == "Today is logged" and b.disabled for b in at.button)
    assert db.log_today(uid, date.today(), 10) is False
    assert db.get_user(uid)["aura_points"] == 10


def test_adaptive_plan_after_missed_days():
    at, uid = new_app()
    rid = db.save_roadmap(uid, "Goal", "text", ["Big task one", "Big task two"])
    with db.get_engine().begin() as conn:  # pretend the account is 6 days old, nothing logged
        conn.execute(update(db.users).where(db.users.c.id == uid)
                     .values(created_at=datetime.now() - timedelta(days=6)))
    go(at, "Progress")
    assert any("not logged progress" in w.value for w in at.warning)
    next(b for b in at.button if b.label == "Make my plan lighter").click().run()
    assert not at.exception
    names = [t["description"] for t in db.get_tasks(uid, rid)]
    assert names == ["Read one page", "Write one line of code"]


def test_low_mood_offers_simplify():
    at, uid = new_app()
    db.save_roadmap(uid, "Goal", "text", ["Big task"])
    at.sidebar.select_slider(key="mood").set_value("Drained")
    go(at, "Progress")
    assert any("Simplify" in b.label for b in at.button)


def test_weekly_review_and_pdf_export():
    at, uid = new_app()
    db.save_roadmap(uid, "Goal", "text", ["Task"])
    go(at, "Progress")
    next(b for b in at.button if b.label == "Write my weekly review").click().run()
    assert not at.exception and any("helpful answer" in m.value for m in at.markdown)


def test_study_flashcards_review_quiz_reading():
    at, uid = new_app()
    db.save_roadmap(uid, "Goal", "text", ["Task A"])
    go(at, "Study")
    at.radio(key="study_section").set_value("Make flashcards").run()
    next(b for b in at.button if b.label == "Generate flashcards").click().run()
    assert not at.exception and db.count_cards(uid) == 4

    at.radio(key="study_section").set_value("Review flashcards").run()
    next(b for b in at.button if b.label == "Show answer").click().run()
    next(b for b in at.button if b.label == "Good").click().run()
    assert not at.exception and len(db.get_due_cards(uid, date.today())) == 3

    at.radio(key="study_section").set_value("Quiz").run()
    next(b for b in at.button if "new 5-question quiz" in b.label).click().run()
    assert not at.exception and len(quiz_radios(at)) == 3
    # submitting with nothing chosen warns
    next(b for b in at.button if b.label == "Submit answers").click().run()
    assert any("answer every question" in w.value for w in at.warning)
    for q in quiz_radios(at):
        q.set_value("x")  # option x is the right answer in the fake quiz
    next(b for b in at.button if b.label == "Submit answers").click().run()
    assert not at.exception
    assert any("Score: 3 / 3" in s.value for s in at.subheader)

    at.radio(key="study_section").set_value("Reading list").run()
    next(b for b in at.button if b.label == "Suggest reading list").click().run()
    assert not at.exception
    assert any("Python Crash Course" in m.value for m in at.markdown)


def test_quiz_missed_questions_become_flashcards():
    at, uid = new_app()
    db.save_roadmap(uid, "Goal", "text", ["Task A"])
    go(at, "Study")
    at.radio(key="study_section").set_value("Quiz").run()
    next(b for b in at.button if "new 5-question quiz" in b.label).click().run()
    for q in quiz_radios(at):
        q.set_value("w")  # wrong on purpose
    next(b for b in at.button if b.label == "Submit answers").click().run()
    next(b for b in at.button if "missed questions" in b.label).click().run()
    assert not at.exception and db.count_cards(uid) == 3


def test_notes_question_answered_from_uploaded_text():
    at, uid = new_app()
    db.add_document(uid, "ml.txt", ["Gradient descent lowers the loss step by step."])
    go(at, "My Notes")
    at.text_input[0].input("what is gradient descent")
    next(b for b in at.button if b.label == "Ask").click().run()
    assert not at.exception and any("helpful answer" in m.value for m in at.markdown)
    at.text_input[0].input("zebra migration")
    next(b for b in at.button if b.label == "Ask").click().run()
    assert any("no matching passage" in i.value for i in at.info)


def test_leaderboard_and_profile_validation():
    at, uid = new_app()
    go(at, "Profile")
    at.checkbox[0].check()  # opt in without nickname
    next(b for b in at.button if b.label == "Save settings").click().run()
    assert any("nickname" in e.value.lower() for e in at.error)
    at.text_input[0].input("StarLearner")
    next(b for b in at.button if b.label == "Save settings").click().run()
    assert not at.exception and db.get_user(uid)["show_on_leaderboard"] == 1
    go(at, "Leaderboard")
    assert not at.exception and at.dataframe


def test_coach_and_history_activation():
    at, uid = new_app()
    db.save_roadmap(uid, "First", "plan one", ["t"])
    first = db.get_active_roadmap(uid)["id"]
    db.save_roadmap(uid, "Second", "plan two", ["t"])
    go(at, "Coach & History")
    at.text_area[0].input("what is a loop")
    next(b for b in at.button if b.label == "Get guidance").click().run()
    assert not at.exception and any("helpful answer" in m.value for m in at.markdown)
    next(b for b in at.button if b.label == "Activate").click().run()
    assert db.get_active_roadmap(uid)["id"] == first


def test_delete_account():
    at, uid = new_app()
    go(at, "Profile")
    at.checkbox[-1].check().run()
    next(b for b in at.button if b.label == "Delete my account").click().run()
    assert not at.exception and db.get_user(uid) is None
