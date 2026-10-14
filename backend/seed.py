"""Seed the configured SQLite database with demo volunteer slots."""

from pathlib import Path

from app.config import DB_PATH
from app.db import get_connection, init_db

DEMO_SLOTS: tuple[tuple[int, str, str, str, int, int], ...] = (
    # booked stays 0: it must equal the real booking rows, and seeding inserts none.
    (1, "2026-10-17", "09:00", "12:00", 10, 0),
    (1, "2026-10-17", "13:00", "16:00", 8, 0),
    (1, "2026-10-18", "09:00", "12:00", 6, 0),
    (2, "2026-10-18", "13:00", "16:00", 12, 0),
    (2, "2026-10-19", "09:00", "12:00", 2, 0),  # small slot to demo "full" quickly
)


def seed_demo_slots(db_path: str | Path | None = None) -> int:
    """Create tables and insert demo slots if the database has no slots."""
    configured_path = db_path if db_path is not None else DB_PATH
    init_db(configured_path)
    conn = get_connection(configured_path)
    try:
        existing = conn.execute("SELECT COUNT(*) FROM volunteer_slots").fetchone()[0]
        if existing:
            return 0
        conn.executemany(
            """
            INSERT INTO volunteer_slots
                (event_id, date, start_time, end_time, capacity, booked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            DEMO_SLOTS,
        )
        return len(DEMO_SLOTS)
    finally:
        conn.close()


if __name__ == "__main__":
    count = seed_demo_slots()
    print(f"Seeded {count} demo slots.")
