"""conftest.py - shared test setup: every test gets a brand-new empty database."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    from core import config, database as db
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    db.reset_engine()
    db.init_db()
    yield
    db.get_engine().dispose()
    db.reset_engine()
