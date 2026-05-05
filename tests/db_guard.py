import os

from webapp.db import get_connection

FORBIDDEN_DATABASES = {"dekorcrm"}


def guard_live_database():
    current_db = _current_database()
    if current_db.lower() in FORBIDDEN_DATABASES:
        raise RuntimeError(
            f"Refusing to run destructive tests against live database '{current_db}'. "
            f"Set TEST_DATABASE or run against a test database."
        )


def _current_database():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            row = cur.fetchone()
            return row["current_database"]


def is_live_database():
    return _current_database().lower() in FORBIDDEN_DATABASES