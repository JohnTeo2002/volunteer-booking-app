"""Concurrency regression test for POST /book (Issue #13)."""

from concurrent.futures import ThreadPoolExecutor

from app.db import get_connection, init_db
from fastapi.testclient import TestClient


def test_ten_concurrent_requests_for_five_spots(tmp_path, monkeypatch):
    """Only five of ten concurrent booking requests can claim a five-capacity slot."""
    db_path = tmp_path / "concurrency.db"
    init_db(db_path)
    monkeypatch.setattr("app.db.DB_PATH", str(db_path))

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO volunteer_slots
                (event_id, date, start_time, end_time, capacity, booked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (1, "2026-10-17", "09:00", "12:00", 5, 0),
        )
    finally:
        conn.close()

    # Import after conftest establishes ADMIN_TOKEN and disables rate limiting.
    from app.main import app

    def attempt(index: int) -> int:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/book",
                json={
                    "slot_id": 1,
                    "volunteer_name": f"Volunteer {index}",
                    "email": f"volunteer{index}@example.com",
                    "phone": "555-1234",
                },
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=10) as executor:
        statuses = list(executor.map(attempt, range(10)))

    assert statuses.count(201) == 5
    assert statuses.count(409) == 5

    conn = get_connection(db_path)
    try:
        slot = conn.execute(
            "SELECT booked FROM volunteer_slots WHERE id = ?", (1,)
        ).fetchone()
        booking_count = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE slot_id = ?", (1,)
        ).fetchone()[0]

        assert slot["booked"] == 5
        assert booking_count == 5
    finally:
        conn.close()
