"""Database connection and initialization module for SQLite."""

import os
from pathlib import Path
import sqlite3

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
