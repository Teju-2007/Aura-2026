"""auth.py - sign up and log in safely.

Passwords are NEVER stored. We store a bcrypt "hash": a one-way scrambled form that
cannot be turned back into the password, even by us.
"""
import re

import bcrypt

from core import database as db

_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")
MAX_PASSWORD_LEN = 64  # bcrypt only reads the first 72 bytes; we keep a safe limit


def validate_username(username: str):
    if not _USERNAME_RE.match(username):
        return "Username must be 3-30 characters: lowercase letters, numbers or underscore."
    return None


def validate_password(password: str):
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > MAX_PASSWORD_LEN:
        return f"Password must be at most {MAX_PASSWORD_LEN} characters."
    return None


def register(username: str, password: str):
    """Return (user_id or None, message)."""
    username = (username or "").strip().lower()
    password = password or ""
    problem = validate_username(username) or validate_password(password)
    if problem:
        return None, problem
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_id = db.create_user(username, hashed)
    if user_id is None:
        return None, "That username is already taken."
    return user_id, "Account created."


def login(username: str, password: str):
    """Return the user dict if the credentials are right, otherwise None."""
    username = (username or "").strip().lower()
    password = password or ""
    user = db.get_user_by_name(username)
    if not user or len(password) > MAX_PASSWORD_LEN:
        return None
    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8"))
    except ValueError:
        return None
    return user if ok else None
