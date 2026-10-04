"""send_reminders.py - emails learners who have not logged progress today.

Run it once a day with a scheduler (cron on Linux/Mac, Task Scheduler on Windows,
or a free GitHub Actions schedule). Test first with:  python send_reminders.py --dry-run
"""
import argparse
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

from core import config
from core import database as db


def build_message(user: dict) -> EmailMessage:
    name = user.get("nickname") or user["username"]
    msg = EmailMessage()
    msg["Subject"] = "Your Aura check-in: 5 minutes is enough today"
    msg["From"] = config.SMTP_FROM
    msg["To"] = user["email"]
    msg.set_content(
        f"Hi {name},\n\nYou have not logged progress today yet. Even a tiny step keeps your "
        "streak alive: review a few flashcards or read one page.\n\n"
        "You can turn these emails off any time in Profile > Email reminders.\n\n- Aura"
    )
    return msg


def main(dry_run: bool = False) -> int:
    db.init_db()
    pending = db.users_to_remind(date.today())
    print(f"{len(pending)} learner(s) to remind.")
    if dry_run:
        for user in pending:
            print(f" would email {user['email']}")
        return 0
    if not (config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD):
        print("SMTP settings are missing in .env, cannot send.")
        return 1
    failures = 0
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        for user in pending:
            try:
                server.send_message(build_message(user))
                print(f" sent to {user['email']}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f" FAILED for {user['email']}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="list who would be emailed")
    sys.exit(main(parser.parse_args().dry_run))
