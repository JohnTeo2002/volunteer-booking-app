"""Schema creation and constraint tests against a real file-backed SQLite DB.

Uses pytest's tmp_path. Not :memory: because the concurrency tests need a shared file.
Pytest is installed through requirements-dev.txt.
"""

import sqlite3

import pytest

from app.db import get_connection, init_db


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


@pytest.fixture
def conn(db_path):
    connection = get_connection(db_path)
    yield connection
    connection.close()


def insert_slot(conn, capacity=2, booked=0):
    cur = conn.execute(
        "INSERT INTO volunteer_slots (event_id, date, start_time, end_time, capacity, booked) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "2026-10-17", "09:00", "12:00", capacity, booked),
    )
    return cur.lastrowid


def insert_booking(conn, slot_id, email="jane@example.com"):
    conn.execute(
        "INSERT INTO bookings (slot_id, volunteer_name, email, phone) VALUES (?, ?, ?, ?)",
        (slot_id, "Jane", email, "555-1234"),
    )


def test_init_creates_both_tables(db_path):
    conn = get_connection(db_path)
    try:
        for table in ("volunteer_slots", "bookings"):
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = ? AND name = ?",
                ("table", table),
            ).fetchone()
            assert row is not None, f"missing table {table}"
    finally:
        conn.close()


def test_init_twice_succeeds(db_path):
    init_db(db_path)  # second call must not raise


def test_duplicate_slot_email_is_rejected(conn):
    slot_id = insert_slot(conn)
    insert_booking(conn, slot_id)
    with pytest.raises(sqlite3.IntegrityError):
        insert_booking(conn, slot_id)


def test_booked_over_capacity_is_rejected(conn):
    slot_id = insert_slot(conn, capacity=2)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE volunteer_slots SET booked = ? WHERE id = ?", (3, slot_id))


def test_foreign_keys_pragma_is_on(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_booking_with_missing_slot_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        insert_booking(conn, slot_id=999)
