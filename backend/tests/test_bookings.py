"""Tests for the atomic POST /book transaction and API contract."""

from concurrent.futures import ThreadPoolExecutor
import sqlite3
import os

import pytest
from fastapi.testclient import TestClient

from app.db import get_connection, init_db
os.environ.setdefault("ADMIN_TOKEN", "secret-token")

from app.main import app


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Use a real, isolated file-backed database for each test."""
    path = tmp_path / "bookings.db"
    init_db(path)
    monkeypatch.setattr("app.db.DB_PATH", str(path))
    return path


@pytest.fixture
def client(db_path):
    """Return a client with unhandled exceptions represented as HTTP 500."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def insert_slot(db_path, capacity=2):
    """Insert an empty slot with the requested capacity."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO volunteer_slots "
            "(event_id, date, start_time, end_time, capacity, booked) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (1, "2026-10-17", "09:00", "12:00", capacity, 0),
        )
        return cursor.lastrowid
    finally:
        conn.close()


def payload(slot_id, email="jane@example.com"):
    """Build a valid booking request."""
    return {
        "slot_id": slot_id,
        "volunteer_name": "Jane",
        "email": email,
        "phone": "555-1234",
    }


def assert_consistent(db_path, slot_id, expected):
    """Verify booked equals the number of persisted booking rows."""
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


@pytest.fixture(autouse=True)
def assert_all_slot_counters_match_booking_rows(request):
    """After each booking test, ensure booked matches persisted booking rows."""
    yield
    db_path = request.getfixturevalue("db_path")
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, booked FROM volunteer_slots ORDER BY id"
        ).fetchall()
        for row in rows:
            booking_count = conn.execute(
                "SELECT COUNT(*) FROM bookings WHERE slot_id = ?", (row["id"],)
            ).fetchone()[0]
            assert row["booked"] == booking_count
    finally:
        conn.close()


def test_success_returns_201_booking_and_increments_once(client, db_path):
    """Successful booking creates exactly one row and returns ISO UTC time."""
    slot_id = insert_slot(db_path)
    response = client.post("/book", json=payload(slot_id))
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id", "slot_id", "volunteer_name", "email", "phone", "created_at"
    }
    assert body["slot_id"] == slot_id
    assert body["email"] == "jane@example.com"
    assert body["created_at"].endswith("Z")
    assert "T" in body["created_at"]
    assert_consistent(db_path, slot_id, 1)


def test_missing_slot_returns_404(client, db_path):
    """Nonexistent slots do not create bookings."""
    response = client.post("/book", json=payload(999))
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "SLOT_NOT_FOUND", "message": "Slot not found.", "details": None
    }
    conn = get_connection(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 0
    finally:
        conn.close()


def test_full_slot_returns_409_without_increment(client, db_path):
    """A full slot is detected by conditional UPDATE rowcount."""
    slot_id = insert_slot(db_path, capacity=1)
    assert client.post("/book", json=payload(slot_id)).status_code == 201
    response = client.post("/book", json=payload(slot_id, "other@example.com"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_FULL"
    assert_consistent(db_path, slot_id, 1)


def test_duplicate_email_rolls_back_counter(client, db_path):
    """Duplicate normalized email must roll back the counter increment."""
    slot_id = insert_slot(db_path, capacity=3)
    assert client.post("/book", json=payload(slot_id)).status_code == 201
    response = client.post("/book", json=payload(slot_id, " JANE@EXAMPLE.COM "))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_BOOKING"
    assert_consistent(db_path, slot_id, 1)


@pytest.mark.parametrize(
    "overrides",
    [
        {"slot_id": 0},
        {"volunteer_name": "  "},
        {"email": "invalid"},
        {"phone": "123"},
    ],
)
def test_invalid_request_returns_422(client, db_path, overrides):
    """Invalid booking fields do not change the database."""
    slot_id = insert_slot(db_path)
    request = payload(slot_id)
    request.update(overrides)
    response = client.post("/book", json=request)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert_consistent(db_path, slot_id, 0)


def test_same_email_can_book_different_slots(client, db_path):
    """Uniqueness applies to a slot and normalized email together."""
    first = insert_slot(db_path)
    second = insert_slot(db_path)
    assert client.post("/book", json=payload(first)).status_code == 201
    assert client.post("/book", json=payload(second)).status_code == 201
    assert_consistent(db_path, first, 1)
    assert_consistent(db_path, second, 1)


def test_concurrent_booking_never_overbooks(client, db_path):
    """Ten simultaneous volunteers compete for five spots."""
    slot_id = insert_slot(db_path, capacity=5)

    def attempt(index):
        return client.post(
            "/book", json=payload(slot_id, f"volunteer{index}@example.com")
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(attempt, range(10)))

    assert sum(r.status_code == 201 for r in responses) == 5
    assert sum(r.status_code == 409 for r in responses) == 5
    assert all(
        r.json()["error"]["code"] == "SLOT_FULL"
        for r in responses if r.status_code == 409
    )
    assert_consistent(db_path, slot_id, 5)


def test_rollback_on_unexpected_insert_failure(db_path):
    """Unexpected database failures must not leave a booked increment."""
    from app.db import create_booking

    slot_id = insert_slot(db_path)
    # Trigger an error after the counter update with a temporary SQLite trigger.
    conn = get_connection(db_path)
    try:
        conn.execute(
            "CREATE TRIGGER reject_booking BEFORE INSERT ON bookings "
            "BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
        )
    finally:
        conn.close()
    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        create_booking(slot_id, "Jane", "jane@example.com", "555-1234", db_path)
    assert_consistent(db_path, slot_id, 0)
