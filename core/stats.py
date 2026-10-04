"""stats.py - small pure functions that turn "days I logged" into numbers.

"Pure" means: no database, no screen, same input always gives the same output.
That makes them easy to test.
"""
from datetime import date, timedelta
from typing import Iterable


def current_streak(logged: Iterable[date], today: date) -> int:
    """Consecutive logged days. Today not logged yet? The streak stays alive from yesterday."""
    days = set(logged)
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def daily_series(logged: Iterable[date], today: date, window: int = 30):
    """Rows of (date, logged_that_day 0/1, consistency_percent_over_last_7_days).

    Missing days count as 0, so skipping days lowers the score honestly.
    """
    days = set(logged)
    rows = []
    for offset in range(window - 1, -1, -1):
        d = today - timedelta(days=offset)
        last7 = sum(1 for k in range(7) if (d - timedelta(days=k)) in days)
        rows.append((d, 1 if d in days else 0, round(100 * last7 / 7)))
    return rows


def days_since_activity(logged: Iterable[date], account_created: date, today: date) -> int:
    """Days since the last log (or since the account was made if never logged)."""
    days = list(logged)
    reference = max(days) if days else account_created
    return max(0, (today - reference).days)


def aura_level(total_days_logged: int) -> str:
    if total_days_logged < 10:
        return "Apprentice"
    if total_days_logged < 30:
        return "Architect"
    return "Master"
