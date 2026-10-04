"""spaced.py - spaced repetition (the SM-2 method, simplified).

Idea: a flashcard you remember well is shown again after a LONGER gap each time;
a card you forget comes back sooner. This is how you beat the "forgetting curve".
"""
from datetime import date, timedelta

# The four buttons the learner sees -> a quality score used by the SM-2 formula
GRADES = {"Again": 1, "Hard": 3, "Good": 4, "Easy": 5}


def review_card(ease: float, interval_days: int, repetitions: int, grade: str, today: date):
    """Return (new_ease, new_interval_days, new_repetitions, new_due_date)."""
    if grade not in GRADES:
        raise ValueError(f"Unknown grade: {grade}")
    q = GRADES[grade]

    if q < 3:  # forgot it: start the ladder again, show tomorrow
        repetitions = 0
        interval_days = 1
    else:
        repetitions += 1
        if repetitions == 1:
            interval_days = 1
        elif repetitions == 2:
            interval_days = 6
        else:
            interval_days = max(1, round(interval_days * ease))

    # ease = how "easy" this card is for you; it never drops below 1.3
    ease = max(1.3, ease + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    return round(ease, 2), int(interval_days), int(repetitions), today + timedelta(days=interval_days)
