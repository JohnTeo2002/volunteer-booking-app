"""Shared pytest fixtures for isolated file-backed SQLite tests."""

import os

import pytest
from fastapi.testclient import TestClient

# These values are only defaults; callers can still provide their own test config.
os.environ["ADMIN_TOKEN"] = "secret-token"
os.environ["DISABLE_RATE_LIMIT"] = "1"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Initialize a fresh SQLite database stored as a temporary file."""
    from app.db import init_db

    path = tmp_path / "test-app.db"
    init_db(path)
    monkeypatch.setattr("app.db.DB_PATH", str(path))
    return path


@pytest.fixture
def client(db_path):
    """Provide an HTTP client using the app and a file-backed test database."""
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
