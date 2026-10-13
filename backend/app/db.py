"""Database connection and initialization module for SQLite."""

import os
import sqlite3
from pathlib import Path

# Default DB path if DB_PATH environment variable is not set
DEFAULT_DB_PATH = "app.db"
DB_PATH = os.getenv("DB_PATH", DEFAULT_DB_PATH)


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create and return a SQLite connection with row_factory and foreign_keys enabled.

    Connections are unpooled, thread-safe (check_same_thread=False), and have
    manual transaction control (isolation_level=None).
    The caller is responsible for closing the connection.
    """
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    """Initialize the database by executing schema.sql.

    Repeated initialization is safe (due to CREATE TABLE IF NOT EXISTS),
    but does not migrate an existing schema.
    """
    schema_path = Path(__file__).parent.parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    conn = get_connection(db_path)
    try:
        conn.executescript(schema_sql)
    finally:
        conn.close()


def get_slots(
    event_id: int | None = None,
    date: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, int | str]]:
    """Return matching slots without exposing booking PII.

    Compute remaining capacity in SQLite and sort by date, start time, and ID.
    """
    conditions: list[str] = []
    parameters: list[int | str] = []

    if event_id is not None:
        conditions.append("event_id = ?")
        parameters.append(event_id)

    if date is not None:
        conditions.append("date = ?")
        parameters.append(date)

    query = (
        "SELECT id, event_id, date, start_time, end_time, capacity, booked, "
        "(capacity - booked) AS remaining "
        "FROM volunteer_slots"
    )
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY date, start_time, id"

    conn = get_connection(db_path)
    try:
        rows = conn.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
