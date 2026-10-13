"""Unit and integration tests for admin authentication."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.config as app_config
from app.db import get_connection


def insert_slot(db_path):
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO volunteer_slots "
            "(event_id, date, start_time, end_time, capacity, booked) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (1, "2026-10-17", "09:00", "12:00", 20, 0),
        )
        return cursor.lastrowid
    finally:
        conn.close()


def test_admin_booking_missing_token_returns_403(client, db_path):
    response = client.get("/booking/1")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_booking_wrong_token_returns_403(client, db_path):
    response = client.get("/booking/1", headers={"X-Admin-Token": "wrong-token"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_empty_admin_secret_returns_403(client, db_path, monkeypatch):
    monkeypatch.setattr(app_config, "ADMIN_TOKEN", "")
    response = client.get("/booking/1", headers={"X-Admin-Token": "secret-token"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_booking_valid_token_can_read_booking(client, db_path):
    from app.db import create_booking

    slot_id = insert_slot(db_path)
    booking = create_booking(
        slot_id, "Jane", "jane@example.com", "555-1234", db_path=db_path
    )
    response = client.get(
        f"/booking/{booking['id']}", headers={"X-Admin-Token": "secret-token"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == booking["id"]
    assert response.json()["created_at"].endswith("Z")


def test_admin_booking_not_found_returns_contract_error(client):
    response = client.get("/booking/999", headers={"X-Admin-Token": "secret-token"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BOOKING_NOT_FOUND"


def test_admin_booking_rate_limit_returns_standard_envelope(client, db_path, monkeypatch):
    from app.db import create_booking
    from app.rate_limit import limiter

    slot_id = insert_slot(db_path)
    booking = create_booking(
        slot_id, "Jane", "jane@example.com", "555-1234", db_path=db_path
    )
    monkeypatch.setattr(limiter, "enabled", True)

    responses = [
        client.get(
            f"/booking/{booking['id']}",
            headers={"X-Admin-Token": "secret-token"},
        )
        for _ in range(11)
    ]
    assert all(response.status_code == 200 for response in responses[:10])
    assert responses[10].status_code == 429
    assert responses[10].json()["error"]["code"] == "RATE_LIMITED"
    assert responses[10].json()["error"]["details"] is None


def test_post_booking_rate_limit_returns_standard_envelope(client, db_path, monkeypatch):
    from app.rate_limit import limiter

    slot_id = insert_slot(db_path)
    monkeypatch.setattr(limiter, "enabled", True)

    responses = [
        client.post(
            "/book",
            json={
                "slot_id": slot_id,
                "volunteer_name": f"Volunteer {index}",
                "email": f"volunteer{index}@example.com",
                "phone": "555-1234",
            },
        )
        for index in range(11)
    ]
    assert all(response.status_code == 201 for response in responses[:10])
    assert responses[10].status_code == 429
    assert responses[10].json()["error"]["code"] == "RATE_LIMITED"


def test_admin_dependency_rejects_non_ascii_token():
    from app.security import require_admin

    with pytest.raises(HTTPException) as exc_info:
        require_admin(x_admin_token="wrong-tøken")
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "UNAUTHORIZED"


def test_empty_admin_token_fails_fast_on_startup(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(main_module, "ADMIN_TOKEN", "")
    with pytest.raises(RuntimeError, match="ADMIN_TOKEN"):
        with TestClient(main_module.app):
            pass
