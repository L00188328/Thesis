import os
import time

import psycopg


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be supplied through the environment or a mounted secret")
    return database_url


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


def database_ready(database_url: str, query: str = "SELECT 1") -> bool:
    try:
        with psycopg.connect(database_url) as conn:
            conn.execute(query)
        return True
    except Exception:
        return False
