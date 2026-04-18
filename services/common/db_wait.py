import os
import time

import psycopg


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/shipments"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def wait_for_db(database_url: str, timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            with psycopg.connect(database_url) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:  # pragma: no cover - startup retry helper
            last_error = exc
            time.sleep(2)

    raise RuntimeError(f"Database did not become ready in time: {last_error}")
