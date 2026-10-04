"""database.py - everything that reads or writes saved data.

Uses SQLAlchemy, so the SAME code works with SQLite (a file on your computer)
and PostgreSQL (a real server). Switch by changing DATABASE_URL in ".env".
All values are passed as parameters (never glued into SQL text), which blocks
SQL injection attacks.
"""
from datetime import date, timedelta
from functools import lru_cache

from sqlalchemy import (
    Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text, UniqueConstraint,
    create_engine, delete, func, insert, select, update,
)
from sqlalchemy.exc import IntegrityError

from core import config

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(40), unique=True, nullable=False),
    Column("password_hash", String(100), nullable=False),
    Column("nickname", String(30), nullable=False, default=""),
    Column("show_on_leaderboard", Integer, nullable=False, default=0),
    Column("aura_points", Integer, nullable=False, default=0),
    Column("language", String(30), nullable=False, default="English"),
    Column("level", String(20), nullable=False, default="Beginner"),
    Column("daily_minutes", Integer, nullable=False, default=30),
    Column("deadline", Date, nullable=True),
    Column("goal_type", String(60), nullable=False, default="Hobby / curiosity"),
    Column("intensity", String(20), nullable=False, default="Balanced"),
    Column("email", String(120), nullable=False, default=""),
    Column("reminders_enabled", Integer, nullable=False, default=0),
    Column("onboarded", Integer, nullable=False, default=0),
    Column("created_at", DateTime, server_default=func.now()),
)

roadmaps = Table(
    "roadmaps", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("title", String(200), nullable=False),
    Column("content", Text, nullable=False),
    Column("is_active", Integer, nullable=False, default=0),
    Column("created_at", DateTime, server_default=func.now()),
)

tasks = Table(
    "tasks", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("roadmap_id", Integer, nullable=False, index=True),
    Column("description", Text, nullable=False),
    Column("is_done", Integer, nullable=False, default=0),
    Column("resources", Text, nullable=False, default=""),  # saved reading list (JSON text)
    Column("created_at", DateTime, server_default=func.now()),
)

progress = Table(
    "progress", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("day", Date, nullable=False),
    Column("completed", Integer, nullable=False, default=1),
    UniqueConstraint("user_id", "day", name="one_log_per_user_per_day"),
)

chat_messages = Table(
    "chat_messages", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("role", String(12), nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
)

flashcards = Table(
    "flashcards", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("task_id", Integer, nullable=True),
    Column("front", Text, nullable=False),
    Column("back", Text, nullable=False),
    Column("ease", Float, nullable=False, default=2.5),
    Column("interval_days", Integer, nullable=False, default=0),
    Column("repetitions", Integer, nullable=False, default=0),
    Column("due", Date, nullable=False),
)

card_reviews = Table(
    "card_reviews", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("day", Date, nullable=False),
    Column("grade", String(10), nullable=False),
)

quiz_results = Table(
    "quiz_results", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("task_id", Integer, nullable=True),
    Column("score", Integer, nullable=False),
    Column("total", Integer, nullable=False),
    Column("day", Date, nullable=False),
)

documents = Table(
    "documents", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("filename", String(200), nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
)

doc_chunks = Table(
    "doc_chunks", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("doc_id", Integer, nullable=False, index=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("position", Integer, nullable=False),
    Column("text", Text, nullable=False),
)

# Columns a user is allowed to change through update_user()
_EDITABLE_USER_FIELDS = {
    "nickname", "show_on_leaderboard", "language", "level", "daily_minutes", "deadline",
    "goal_type", "intensity", "email", "reminders_enabled", "onboarded",
}


@lru_cache(maxsize=1)
def get_engine():
    kwargs = {"pool_pre_ping": True}
    if config.DATABASE_URL.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(config.DATABASE_URL, **kwargs)


def reset_engine():
    """Forget the cached engine (used by tests that switch databases)."""
    get_engine.cache_clear()


def init_db():
    """Create every table that does not exist yet. Safe to call many times."""
    metadata.create_all(get_engine())


def _row(result_row):
    return dict(result_row._mapping) if result_row is not None else None


def _rows(result):
    return [dict(r._mapping) for r in result]


# ------------------------------------------------------------------ users
def create_user(username: str, password_hash: str):
    """Return the new user's id, or None if the username already exists."""
    try:
        with get_engine().begin() as conn:
            res = conn.execute(insert(users).values(username=username, password_hash=password_hash))
            return int(res.inserted_primary_key[0])
    except IntegrityError:
        return None


def get_user_by_name(username: str):
    with get_engine().connect() as conn:
        return _row(conn.execute(select(users).where(users.c.username == username)).first())


def get_user(user_id: int):
    with get_engine().connect() as conn:
        return _row(conn.execute(select(users).where(users.c.id == user_id)).first())


def update_user(user_id: int, **fields):
    clean = {k: v for k, v in fields.items() if k in _EDITABLE_USER_FIELDS}
    if not clean:
        return
    with get_engine().begin() as conn:
        conn.execute(update(users).where(users.c.id == user_id).values(**clean))


def get_leaderboard(limit: int = 10):
    """Only users who opted in. Returns (display_name, points). Never real usernames."""
    stmt = (
        select(users.c.nickname, users.c.aura_points)
        .where(users.c.show_on_leaderboard == 1)
        .order_by(users.c.aura_points.desc(), users.c.id.asc())
        .limit(limit)
    )
    with get_engine().connect() as conn:
        return [((nick or "Anonymous"), pts) for nick, pts in conn.execute(stmt)]


def delete_user(user_id: int):
    """Erase the account and everything connected to it."""
    with get_engine().begin() as conn:
        for table in (roadmaps, tasks, progress, chat_messages, flashcards, card_reviews,
                      quiz_results, documents, doc_chunks):
            conn.execute(delete(table).where(table.c.user_id == user_id))
        conn.execute(delete(users).where(users.c.id == user_id))


# --------------------------------------------------------- roadmaps & tasks
def save_roadmap(user_id: int, title: str, content: str, task_list):
    """Save a new roadmap, make it the active one, and store its tasks."""
    with get_engine().begin() as conn:
        conn.execute(update(roadmaps).where(roadmaps.c.user_id == user_id).values(is_active=0))
        res = conn.execute(insert(roadmaps).values(
            user_id=user_id, title=title[:200], content=content, is_active=1))
        rid = int(res.inserted_primary_key[0])
        for desc in task_list:
            conn.execute(insert(tasks).values(user_id=user_id, roadmap_id=rid, description=desc))
    return rid


def get_active_roadmap(user_id: int):
    with get_engine().connect() as conn:
        stmt = select(roadmaps).where(roadmaps.c.user_id == user_id, roadmaps.c.is_active == 1)
        return _row(conn.execute(stmt).first())


def get_roadmaps(user_id: int):
    with get_engine().connect() as conn:
        stmt = select(roadmaps).where(roadmaps.c.user_id == user_id).order_by(roadmaps.c.id.desc())
        return _rows(conn.execute(stmt))


def set_active_roadmap(user_id: int, roadmap_id: int):
    with get_engine().begin() as conn:
        conn.execute(update(roadmaps).where(roadmaps.c.user_id == user_id).values(is_active=0))
        conn.execute(update(roadmaps).where(
            roadmaps.c.user_id == user_id, roadmaps.c.id == roadmap_id).values(is_active=1))


def get_tasks(user_id: int, roadmap_id: int):
    with get_engine().connect() as conn:
        stmt = (select(tasks).where(tasks.c.user_id == user_id, tasks.c.roadmap_id == roadmap_id)
                .order_by(tasks.c.id.asc()))
        return _rows(conn.execute(stmt))


def get_task(user_id: int, task_id: int):
    with get_engine().connect() as conn:
        stmt = select(tasks).where(tasks.c.user_id == user_id, tasks.c.id == task_id)
        return _row(conn.execute(stmt).first())


def set_task_done(user_id: int, task_id: int, done: bool):
    with get_engine().begin() as conn:
        conn.execute(update(tasks).where(tasks.c.user_id == user_id, tasks.c.id == task_id)
                     .values(is_done=1 if done else 0))


def replace_open_tasks(user_id: int, roadmap_id: int, new_tasks):
    """Delete the NOT-done tasks and insert the new ones (finished tasks are kept)."""
    with get_engine().begin() as conn:
        conn.execute(delete(tasks).where(
            tasks.c.user_id == user_id, tasks.c.roadmap_id == roadmap_id, tasks.c.is_done == 0))
        for desc in new_tasks:
            conn.execute(insert(tasks).values(user_id=user_id, roadmap_id=roadmap_id, description=desc))


def save_task_resources(user_id: int, task_id: int, resources_json: str):
    with get_engine().begin() as conn:
        conn.execute(update(tasks).where(tasks.c.user_id == user_id, tasks.c.id == task_id)
                     .values(resources=resources_json))


# ----------------------------------------------------------------- progress
def log_today(user_id: int, day: date, points: int) -> bool:
    """Record today's success ONCE per day and award points. False if already logged."""
    try:
        with get_engine().begin() as conn:
            conn.execute(insert(progress).values(user_id=user_id, day=day, completed=1))
            conn.execute(update(users).where(users.c.id == user_id)
                         .values(aura_points=users.c.aura_points + points))
    except IntegrityError:
        return False
    return True


def logged_days(user_id: int):
    with get_engine().connect() as conn:
        stmt = select(progress.c.day).where(progress.c.user_id == user_id)
        return [r[0] for r in conn.execute(stmt)]


# --------------------------------------------------------------------- chat
def add_message(user_id: int, role: str, content: str):
    with get_engine().begin() as conn:
        conn.execute(insert(chat_messages).values(user_id=user_id, role=role, content=content))


def get_messages(user_id: int, limit: int = 50):
    """The newest `limit` messages, oldest first."""
    with get_engine().connect() as conn:
        stmt = (select(chat_messages.c.role, chat_messages.c.content)
                .where(chat_messages.c.user_id == user_id)
                .order_by(chat_messages.c.id.desc()).limit(limit))
        rows = [{"role": r, "content": c} for r, c in conn.execute(stmt)]
    return list(reversed(rows))


def clear_messages(user_id: int):
    with get_engine().begin() as conn:
        conn.execute(delete(chat_messages).where(chat_messages.c.user_id == user_id))


# --------------------------------------------------------------- flashcards
def add_flashcards(user_id: int, task_id, cards, today: date) -> int:
    with get_engine().begin() as conn:
        for card in cards:
            conn.execute(insert(flashcards).values(
                user_id=user_id, task_id=task_id, front=card["front"], back=card["back"],
                ease=2.5, interval_days=0, repetitions=0, due=today))
    return len(cards)


def get_due_cards(user_id: int, today: date, limit: int = 50):
    with get_engine().connect() as conn:
        stmt = (select(flashcards).where(flashcards.c.user_id == user_id, flashcards.c.due <= today)
                .order_by(flashcards.c.due.asc(), flashcards.c.id.asc()).limit(limit))
        return _rows(conn.execute(stmt))


def count_cards(user_id: int, task_id=None) -> int:
    stmt = select(func.count()).select_from(flashcards).where(flashcards.c.user_id == user_id)
    if task_id is not None:
        stmt = stmt.where(flashcards.c.task_id == task_id)
    with get_engine().connect() as conn:
        return int(conn.execute(stmt).scalar() or 0)


def save_card_review(user_id: int, card_id: int, ease, interval_days, repetitions, due, grade, today):
    with get_engine().begin() as conn:
        conn.execute(update(flashcards).where(
            flashcards.c.user_id == user_id, flashcards.c.id == card_id
        ).values(ease=ease, interval_days=interval_days, repetitions=repetitions, due=due))
        conn.execute(insert(card_reviews).values(user_id=user_id, day=today, grade=grade))


def get_card(user_id: int, card_id: int):
    with get_engine().connect() as conn:
        stmt = select(flashcards).where(flashcards.c.user_id == user_id, flashcards.c.id == card_id)
        return _row(conn.execute(stmt).first())


# ------------------------------------------------------------------ quizzes
def save_quiz_result(user_id: int, task_id, score: int, total: int, today: date):
    with get_engine().begin() as conn:
        conn.execute(insert(quiz_results).values(
            user_id=user_id, task_id=task_id, score=score, total=total, day=today))


# ------------------------------------------------------------ notes (RAG)
def add_document(user_id: int, filename: str, chunks) -> int:
    with get_engine().begin() as conn:
        res = conn.execute(insert(documents).values(user_id=user_id, filename=filename[:200]))
        doc_id = int(res.inserted_primary_key[0])
        for pos, text in enumerate(chunks):
            conn.execute(insert(doc_chunks).values(
                doc_id=doc_id, user_id=user_id, position=pos, text=text))
    return doc_id


def list_documents(user_id: int):
    with get_engine().connect() as conn:
        stmt = select(documents).where(documents.c.user_id == user_id).order_by(documents.c.id.desc())
        return _rows(conn.execute(stmt))


def delete_document(user_id: int, doc_id: int):
    with get_engine().begin() as conn:
        conn.execute(delete(doc_chunks).where(
            doc_chunks.c.user_id == user_id, doc_chunks.c.doc_id == doc_id))
        conn.execute(delete(documents).where(
            documents.c.user_id == user_id, documents.c.id == doc_id))


def get_all_chunks(user_id: int):
    """Every chunk of the user's notes, with its file name."""
    with get_engine().connect() as conn:
        stmt = (select(doc_chunks.c.text, documents.c.filename)
                .join(documents, documents.c.id == doc_chunks.c.doc_id)
                .where(doc_chunks.c.user_id == user_id)
                .order_by(doc_chunks.c.doc_id, doc_chunks.c.position))
        return [{"text": t, "filename": f} for t, f in conn.execute(stmt)]


# ---------------------------------------------------------- summaries etc.
def weekly_stats(user_id: int, today: date) -> dict:
    """Plain numbers about the last 7 days (fed to the weekly AI summary)."""
    since = today - timedelta(days=6)
    with get_engine().connect() as conn:
        days_logged = conn.execute(
            select(func.count()).select_from(progress)
            .where(progress.c.user_id == user_id, progress.c.day >= since)).scalar() or 0
        reviews = conn.execute(
            select(func.count()).select_from(card_reviews)
            .where(card_reviews.c.user_id == user_id, card_reviews.c.day >= since)).scalar() or 0
        quiz = conn.execute(
            select(func.count(), func.coalesce(func.sum(quiz_results.c.score), 0),
                   func.coalesce(func.sum(quiz_results.c.total), 0))
            .where(quiz_results.c.user_id == user_id, quiz_results.c.day >= since)).first()
    quizzes_taken, score_sum, total_sum = int(quiz[0]), int(quiz[1]), int(quiz[2])
    return {
        "days_logged_last_7": int(days_logged),
        "flashcard_reviews_last_7": int(reviews),
        "quizzes_taken_last_7": quizzes_taken,
        "quiz_average_percent": round(100 * score_sum / total_sum) if total_sum else None,
    }


def users_to_remind(today: date):
    """Users who want email reminders, have an email, and have not logged today."""
    with get_engine().connect() as conn:
        logged_today = select(progress.c.user_id).where(progress.c.day == today)
        stmt = select(users).where(
            users.c.reminders_enabled == 1, users.c.email != "", users.c.id.not_in(logged_today))
        return _rows(conn.execute(stmt))
