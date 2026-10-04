"""test_core.py - checks the non-screen parts: database, login, AI parsing, notes, reports."""
from datetime import date, timedelta

import pytest

from core import ai, auth, config, retrieval, spaced, stats
from core import database as db
from core.report import build_progress_pdf

TODAY = date(2026, 10, 4)


def make_user(name="tejaveni"):
    uid, _ = auth.register(name, "password123")
    return uid


# ---------------------------------------------------------------- auth
def test_register_and_login():
    uid, msg = auth.register("Teju_01", "password123")
    assert uid and msg == "Account created."
    assert auth.login("teju_01", "password123")["id"] == uid
    assert auth.login("teju_01", "wrongpass1") is None
    assert auth.login("nobody", "password123") is None


def test_register_rules():
    assert auth.register("ab", "password123")[0] is None
    assert auth.register("good_name", "short")[0] is None
    assert auth.register("good_name", "x" * 65)[0] is None
    make_user("same")
    assert auth.register("same", "password123")[1] == "That username is already taken."


def test_password_is_hashed():
    uid = make_user()
    assert "password123" not in db.get_user(uid)["password_hash"]


# ------------------------------------------------------------ db: points
def test_one_log_per_day_and_points():
    uid = make_user()
    assert db.log_today(uid, TODAY, 10) is True
    assert db.log_today(uid, TODAY, 10) is False  # the old "unlimited points" bug
    assert db.get_user(uid)["aura_points"] == 10
    assert db.log_today(uid, TODAY + timedelta(days=1), 10) is True
    assert db.get_user(uid)["aura_points"] == 20


def test_leaderboard_is_opt_in_and_hides_usernames():
    a, b, c = make_user("alpha"), make_user("bravo"), make_user("charlie")
    db.log_today(a, TODAY, 20)
    db.log_today(b, TODAY, 5)
    db.update_user(a, nickname="Star", show_on_leaderboard=1)
    db.update_user(b, show_on_leaderboard=1)  # no nickname
    board = db.get_leaderboard()
    assert board == [("Star", 20), ("Anonymous", 5)]
    assert all("charlie" not in name for name, _ in board)


# --------------------------------------------------- roadmaps and tasks
def test_roadmap_tasks_and_replace_keeps_done():
    uid = make_user()
    rid = db.save_roadmap(uid, "Learn ML", "Blueprint", ["A", "B", "C"])
    assert db.get_active_roadmap(uid)["id"] == rid
    tasks = db.get_tasks(uid, rid)
    db.set_task_done(uid, tasks[0]["id"], True)
    db.replace_open_tasks(uid, rid, ["B small", "C small"])
    names = [t["description"] for t in db.get_tasks(uid, rid)]
    assert names == ["A", "B small", "C small"]  # no duplicates, finished task kept


def test_activate_other_roadmap_and_ownership():
    u1, u2 = make_user("one_user"), make_user("two_user")
    r1 = db.save_roadmap(u1, "First", "x", ["t"])
    r2 = db.save_roadmap(u1, "Second", "y", ["t"])
    assert db.get_active_roadmap(u1)["id"] == r2
    db.set_active_roadmap(u1, r1)
    assert db.get_active_roadmap(u1)["id"] == r1
    task = db.get_tasks(u1, r1)[0]
    db.set_task_done(u2, task["id"], True)  # another user cannot touch it
    assert db.get_tasks(u1, r1)[0]["is_done"] == 0


def test_chat_persistence_and_clear():
    uid = make_user()
    for i in range(5):
        db.add_message(uid, "user", f"m{i}")
    assert [m["content"] for m in db.get_messages(uid, limit=3)] == ["m2", "m3", "m4"]
    db.clear_messages(uid)
    assert db.get_messages(uid) == []


def test_delete_user_removes_everything():
    uid = make_user()
    db.save_roadmap(uid, "G", "c", ["t"])
    db.add_message(uid, "user", "hi")
    db.add_document(uid, "n.txt", ["chunk"])
    db.delete_user(uid)
    assert db.get_user(uid) is None
    assert db.get_messages(uid) == [] and db.list_documents(uid) == []


# ------------------------------------------------------------- flashcards
def test_spaced_repetition_ladder():
    ease, interval, reps, due = spaced.review_card(2.5, 0, 0, "Good", TODAY)
    assert (interval, reps) == (1, 1)
    ease, interval, reps, due = spaced.review_card(ease, interval, reps, "Good", TODAY)
    assert (interval, reps) == (6, 2)
    ease, interval, reps, due = spaced.review_card(ease, interval, reps, "Good", TODAY)
    assert interval == 15 and due == TODAY + timedelta(days=15)
    ease, interval, reps, due = spaced.review_card(ease, interval, reps, "Again", TODAY)
    assert (interval, reps) == (1, 0)
    assert ease >= 1.3
    with pytest.raises(ValueError):
        spaced.review_card(2.5, 0, 0, "Banana", TODAY)


def test_flashcard_flow_and_stats():
    uid = make_user()
    db.add_flashcards(uid, 1, [{"front": "Q1", "back": "A1"}, {"front": "Q2", "back": "A2"}], TODAY)
    assert db.count_cards(uid) == 2 and db.count_cards(uid, 1) == 2 and db.count_cards(uid, 99) == 0
    card = db.get_due_cards(uid, TODAY)[0]
    new = spaced.review_card(card["ease"], card["interval_days"], card["repetitions"], "Good", TODAY)
    db.save_card_review(uid, card["id"], *new, "Good", TODAY)
    assert len(db.get_due_cards(uid, TODAY)) == 1
    assert len(db.get_due_cards(uid, TODAY + timedelta(days=1))) == 2
    db.save_quiz_result(uid, 1, 3, 5, TODAY)
    s = db.weekly_stats(uid, TODAY)
    assert s["flashcard_reviews_last_7"] == 1 and s["quiz_average_percent"] == 60


# ---------------------------------------------------------------- stats
def test_streak_and_series():
    days = [TODAY - timedelta(days=i) for i in (1, 2, 3)]
    assert stats.current_streak(days, TODAY) == 3  # today not logged yet, streak alive
    assert stats.current_streak(days + [TODAY], TODAY) == 4
    assert stats.current_streak([TODAY - timedelta(days=3)], TODAY) == 0
    series = stats.daily_series([TODAY], TODAY, window=30)
    assert len(series) == 30 and series[-1] == (TODAY, 1, 14)  # 1 of 7 days = 14%
    assert stats.days_since_activity([], TODAY - timedelta(days=5), TODAY) == 5
    assert stats.aura_level(0) == "Apprentice" and stats.aura_level(30) == "Master"


# ------------------------------------------------------------------- ai
def test_parse_architect_with_and_without_json():
    plain = ai.parse_architect_output("What is your goal?")
    assert plain["tasks"] == [] and not plain["json_error"]
    raw = 'Blueprint here\n---JSON---\n{"title": "Learn ML", "tasks": ["a", "b", "a", 5]}\n---END---'
    out = ai.parse_architect_output(raw)
    assert out["text"] == "Blueprint here" and out["title"] == "Learn ML" and out["tasks"] == ["a", "b"]
    broken = ai.parse_architect_output("Blueprint\n---JSON---\n{not json\n---END---")
    assert broken["text"] == "Blueprint" and broken["json_error"] and broken["tasks"] == []


def test_extract_json_handles_fences():
    assert ai.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert ai.extract_json("nothing here") is None


def test_clean_quiz_rejects_bad_items():
    good = {"question": "Q?", "options": ["a", "b", "c", "d"], "answer_index": "2", "explanation": "e"}
    bad = [
        {"question": "Q", "options": ["a", "a", "c", "d"], "answer_index": 0},
        {"question": "Q", "options": ["a", "b", "c"], "answer_index": 0},
        {"question": "Q", "options": ["a", "b", "c", "d"], "answer_index": 9},
        {"question": "Q", "options": ["a", "b", "c", "d"], "answer_index": True},
        "junk",
    ]
    result = ai.clean_quiz([good] + bad)
    assert len(result) == 1 and result[0]["answer_index"] == 2


def test_ai_functions_with_fake_model(monkeypatch):
    profile = {"level": "Beginner", "language": "English", "daily_minutes": 30}
    monkeypatch.setattr(ai, "_complete", lambda *a, **k: '{"cards": [{"front": "f", "back": "b"}]}')
    assert ai.make_flashcards("t", "g", profile) == [{"front": "f", "back": "b"}]
    monkeypatch.setattr(ai, "_complete", lambda *a, **k: "not json at all")
    with pytest.raises(ai.AIError):
        ai.make_flashcards("t", "g", profile)
    with pytest.raises(ai.AIError):
        ai.make_quiz("t", "g", profile)
    with pytest.raises(ai.AIError):
        ai.simplify_tasks(["x"], "tired", profile)
    with pytest.raises(ai.AIError):
        ai.suggest_resources("t", "g", profile)


def test_missing_api_key_is_friendly(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    monkeypatch.setattr(ai, "_CLIENT", None)
    with pytest.raises(ai.AIError, match="GROQ_API_KEY"):
        ai._complete([{"role": "user", "content": "hi"}])


def test_api_failure_becomes_ai_error(monkeypatch):
    class Boom:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("network exploded")
    monkeypatch.setattr(config, "GROQ_API_KEY", "x")
    monkeypatch.setattr(ai, "_CLIENT", Boom())
    with pytest.raises(ai.AIError):
        ai._complete([{"role": "user", "content": "hi"}])


# ------------------------------------------------------------ retrieval
def test_chunking_and_search():
    text = " ".join(f"word{i}" for i in range(600))
    chunks = retrieval.chunk_text(text, size=300, overlap=50)
    assert len(chunks) > 3 and all(len(c) <= 300 for c in chunks)
    assert retrieval.chunk_text("   ") == []
    pool = [
        {"text": "Gradient descent updates weights to reduce loss.", "filename": "a.txt"},
        {"text": "Photosynthesis happens in chloroplasts.", "filename": "b.txt"},
    ]
    best = retrieval.top_chunks("How does gradient descent work?", pool, k=1)
    assert best[0]["filename"] == "a.txt"
    assert retrieval.top_chunks("zebra", pool) == []


def test_extract_text_txt_and_bad_types():
    assert retrieval.extract_text("n.md", "h\u00e9llo".encode("utf-8")) == "h\u00e9llo"
    with pytest.raises(ValueError):
        retrieval.extract_text("n.exe", b"x")
    with pytest.raises(ValueError):
        retrieval.extract_text("n.pdf", b"this is not a pdf")


def test_extract_text_real_pdf():
    pdf = build_progress_pdf("Teju", "Goal", "Beginner", 0, 0, [], [], TODAY)
    assert "Aura Progress Report" in retrieval.extract_text("r.pdf", pdf)


# ------------------------------------------------------------- report
def test_report_handles_non_latin_text():
    series = stats.daily_series([TODAY], TODAY)
    name = "\u0c24\u0c47\u0c1c <b>"  # Telugu letters plus a fake HTML tag
    goal = "\u0c32\u0c15\u0c4d\u0c37\u0c4d\u0c2f\u0c02 & goal"
    tasks = [{"description": "Read <page> 1", "is_done": 1}]
    pdf = build_progress_pdf(name, goal, "Beginner", 10, 1, tasks, series, TODAY)
    assert pdf.startswith(b"%PDF")


# ------------------------------------------------------------ reminders
def test_reminders_select_and_send(monkeypatch):
    import send_reminders
    a, b, c = make_user("aaa_user"), make_user("bbb_user"), make_user("ccc_user")
    db.update_user(a, email="a@example.com", reminders_enabled=1)
    db.update_user(b, email="b@example.com", reminders_enabled=1)
    db.update_user(c, email="", reminders_enabled=1)  # no email -> skipped
    db.log_today(b, date.today(), 5)  # already logged -> skipped
    assert [u["email"] for u in db.users_to_remind(date.today())] == ["a@example.com"]
    assert send_reminders.main(dry_run=True) == 0
    assert send_reminders.main(dry_run=False) == 1  # SMTP not configured

    sent = []

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): pass
        def send_message(self, msg): sent.append(msg["To"])

    monkeypatch.setattr(config, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(config, "SMTP_USER", "u")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(send_reminders.smtplib, "SMTP", FakeSMTP)
    assert send_reminders.main(dry_run=False) == 0 and sent == ["a@example.com"]
