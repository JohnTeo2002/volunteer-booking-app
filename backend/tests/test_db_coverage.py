"""Direct database tests that exercise app.db.py branches."""

import sqlite3

import pytest

import app.db as db_module
from app.db import create_booking, get_connection, get_slots, init_db


def insert_slot(db_path, capacity=2, booked=0, event_id=1, date="2026-10-17"):
    """Insert a test slot into a file-backed SQLite database."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO volunteer_slots
                (event_id, date, start_time, end_time, capacity, booked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, date, "09:00", "12:00", capacity, booked),
        )
        return cursor.lastrowid
    finally:
        conn.close()


def assert_consistent(db_path, slot_id, expected):
    """Assert the denormalized counter matches persisted booking rows."""
    conn = get_connection(db_path)
    try:
        booked = conn.execute(
            "SELECT booked FROM volunteer_slots WHERE id = ?", (slot_id,)
        ).fetchone()["booked"]
        count = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE slot_id = ?", (slot_id,)
        ).fetchone()[0]
        assert booked == count == expected
    finally:
        conn.close()


def test_default_db_path_connection_and_initialization(tmp_path, monkeypatch):
    """Cover DB_PATH fallback when connection and initialization omit a path."""
    path = tmp_path / "default-path.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(path))

    init_db()
    conn = get_connection()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()

    slot_id = insert_slot(path)
    assert get_slots()
    assert get_slots(event_id=1)
    assert get_slots(date="2026-10-17")
    assert get_slots(event_id=1, date="2026-10-17")
    assert get_slots(event_id=999) == []
    assert_consistent(path, slot_id, 0)


def test_create_booking_raises_when_inserted_row_cannot_be_read(tmp_path, monkeypatch):
    """The defensive missing-row branch rolls back the capacity increment."""
    path = tmp_path / "missing-inserted-row.db"
    init_db(path)
    slot_id = insert_slot(path)
    real_get_connection = db_module.get_connection

    class EmptySelectCursor:
        def fetchone(self):
            return None

    class ConnectionProxy:
        def __init__(self, connection):
            self.connection = connection

        @property
        def in_transaction(self):
            return self.connection.in_transaction

        def execute(self, sql, parameters=()):
            cursor = self.connection.execute(sql, parameters)
            if sql.startswith(
                "SELECT id, slot_id, volunteer_name, email, phone, created_at "
                "FROM bookings WHERE id = ?"
            ):
                return EmptySelectCursor()
            return cursor

        def close(self):
            self.connection.close()

    monkeypatch.setattr(
        db_module,
        "get_connection",
        lambda db_path=None: ConnectionProxy(real_get_connection(path)),
    )
    with pytest.raises(RuntimeError, match="Inserted booking could not be retrieved"):
        create_booking(slot_id, "Jane", "jane@example.com", "555-1234", path)

    monkeypatch.setattr(db_module, "get_connection", real_get_connection)
    assert_consistent(path, slot_id, 0)


def test_create_booking_skips_rollback_after_transaction_has_committed(
    tmp_path, monkeypatch
):
    """If an error occurs after COMMIT, no invalid ROLLBACK is attempted."""
    path = tmp_path / "post-commit-error.db"
    init_db(path)
    slot_id = insert_slot(path)
    real_get_connection = db_module.get_connection

    class CommitThenFailConnection:
        def __init__(self, connection):
            self.connection = connection

        @property
        def in_transaction(self):
            return self.connection.in_transaction

        def execute(self, sql, parameters=()):
            cursor = self.connection.execute(sql, parameters)
            if sql == "COMMIT":
                raise RuntimeError("simulated post-commit failure")
            return cursor

        def close(self):
            self.connection.close()

    monkeypatch.setattr(
        db_module,
        "get_connection",
        lambda db_path=None: CommitThenFailConnection(real_get_connection(path)),
    )
    with pytest.raises(RuntimeError, match="simulated post-commit failure"):
        create_booking(slot_id, "Jane", "jane@example.com", "555-1234", path)

    monkeypatch.setattr(db_module, "get_connection", real_get_connection)
    assert_consistent(path, slot_id, 1)


def test_create_booking_rethrows_non_unique_integrity_error(tmp_path):
    """A trigger integrity error is not incorrectly classified as a duplicate."""
    path = tmp_path / "trigger-error.db"
    init_db(path)
    slot_id = insert_slot(path)
    conn = get_connection(path)
    try:
        conn.execute(
            "CREATE TRIGGER reject_booking BEFORE INSERT ON bookings "
            "BEGIN SELECT RAISE(ABORT, 'injected trigger error'); END"
        )
    finally:
        conn.close()

    with pytest.raises(sqlite3.IntegrityError, match="injected trigger error"):
        create_booking(slot_id, "Jane", "jane@example.com", "555-1234", path)
    assert_consistent(path, slot_id, 0)
