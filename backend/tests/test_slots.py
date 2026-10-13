"""Unit and integration tests for GET /slots."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_connection, get_slots, init_db
from app.routes.slots import router


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary file-backed SQLite database with representative slots."""
    path = tmp_path / "slots-test.db"
    init_db(path)
    conn = get_connection(path)
    try:
        conn.executemany(
            """
            INSERT INTO volunteer_slots
                (event_id, date, start_time, end_time, capacity, booked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (2, "2026-10-18", "13:00", "16:00", 8, 8),
                (1, "2026-10-17", "13:00", "16:00", 8, 3),
                (1, "2026-10-17", "09:00", "12:00", 10, 4),
                (2, "2026-10-17", "09:00", "12:00", 5, 0),
            ],
        )
    finally:
        conn.close()
    return path


@pytest.fixture
def app(db_path, monkeypatch):
    """Build an isolated test app backed by the fixture database."""

    def fixture_get_slots(event_id=None, date=None):
        return get_slots(event_id=event_id, date=date, db_path=db_path)

    monkeypatch.setattr("app.routes.slots.get_slots", fixture_get_slots)
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create a test client that returns HTTP error responses for assertions."""
    return TestClient(app, raise_server_exceptions=False)


def test_get_slots_returns_only_public_slot_fields(db_path):
    """The database helper returns a bare collection of slot fields without PII."""
    rows = get_slots(db_path=db_path)
    assert len(rows) == 4
    expected_fields = {
        "id",
        "event_id",
        "date",
        "start_time",
        "end_time",
        "capacity",
        "booked",
        "remaining",
    }
    assert all(set(row) == expected_fields for row in rows)
    assert all(
        "email" not in row and "volunteer_name" not in row and "phone" not in row
        for row in rows
    )


def test_get_slots_computes_remaining_and_sorts_results(db_path):
    """Results are ordered by date, start time, and ID with remaining computed."""
    rows = get_slots(db_path=db_path)
    assert [(row["date"], row["start_time"], row["id"]) for row in rows] == [
        ("2026-10-17", "09:00", 3),
        ("2026-10-17", "09:00", 4),
        ("2026-10-17", "13:00", 2),
        ("2026-10-18", "13:00", 1),
    ]
    assert [row["remaining"] for row in rows] == [6, 5, 5, 0]


@pytest.mark.parametrize(("event_id", "expected_count"), [(1, 2), (2, 2), (999, 0)])
def test_get_slots_filters_by_event_id(db_path, event_id, expected_count):
    """The optional event filter returns only slots for that event."""
    rows = get_slots(event_id=event_id, db_path=db_path)
    assert len(rows) == expected_count
    assert all(row["event_id"] == event_id for row in rows)


def test_get_slots_filters_by_date(db_path):
    """The optional date filter returns only slots on the requested date."""
    rows = get_slots(date="2026-10-17", db_path=db_path)
    assert len(rows) == 3
    assert all(row["date"] == "2026-10-17" for row in rows)


def test_get_slots_combines_filters(db_path):
    """Both query filters can be combined."""
    rows = get_slots(event_id=1, date="2026-10-17", db_path=db_path)
    assert len(rows) == 2
    assert all(
        row["event_id"] == 1 and row["date"] == "2026-10-17" for row in rows
    )


def test_list_slots_returns_bare_array_without_pii(client):
    """The endpoint returns a bare array and omits volunteer personal information."""
    response = client.get("/slots")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 4
    expected_fields = {
        "id",
        "event_id",
        "date",
        "start_time",
        "end_time",
        "capacity",
        "booked",
        "remaining",
    }
    assert all(set(row) == expected_fields for row in payload)
    assert [row["remaining"] for row in payload] == [6, 5, 5, 0]


def test_list_slots_filters_query_parameters(client):
    """The endpoint supports event_id and date together."""
    response = client.get("/slots?event_id=1&date=2026-10-17")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert all(row["event_id"] == 1 for row in rows)
    assert all(row["date"] == "2026-10-17" for row in rows)


@pytest.mark.parametrize("event_id", ["0", "-1", "not-an-int"])
def test_list_slots_rejects_invalid_event_id(client, event_id):
    """Non-positive or non-integer event IDs return a validation response."""
    response = client.get(f"/slots?event_id={event_id}")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "date",
    ["17-10-2026", "2026-13-01", "not-a-date", "20261017", "2026-1-7"],
)
def test_list_slots_rejects_invalid_date(client, date):
    """Malformed dates return a validation response."""
    response = client.get(f"/slots?date={date}")
    assert response.status_code == 422
