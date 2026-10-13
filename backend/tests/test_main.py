"""Unit tests for FastAPI main app, error envelopes, and config."""

import os

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

# Ensure ADMIN_TOKEN is set for testing
os.environ["ADMIN_TOKEN"] = "secret-token"

from app.config import ADMIN_TOKEN, CORS_ORIGINS
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_config_admin_token():
    """Verify ADMIN_TOKEN is configured."""
    assert ADMIN_TOKEN == "secret-token"


def test_config_cors_no_wildcard():
    """Verify CORS origins do not contain wildcard."""
    assert "*" not in CORS_ORIGINS


# Add a dummy test endpoint to trigger validation error and http exception
class DummyModel(BaseModel):
    value: int = Field(gt=0)


@app.post("/test-validation")
def dummy_validation(body: DummyModel):
    return {"value": body.value}


@app.get("/test-404")
def dummy_404():
    raise HTTPException(status_code=404, detail="Not found.")


@app.get("/test-structured-error")
def dummy_structured():
    raise HTTPException(
        status_code=409, detail={"code": "SLOT_FULL", "message": "This slot is full."}
    )


@app.get("/test-500")
def dummy_500():
    raise RuntimeError("Internal database failure with secret stack trace")


def test_validation_error_envelope():
    """Verify 422 error returns standard error envelope."""
    response = client.post("/test-validation", json={"value": -1})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in data["error"]
    assert isinstance(data["error"]["details"], list)


def test_not_found_error_envelope():
    """Verify 404 error returns standard error envelope."""
    response = client.get("/test-404")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "SLOT_NOT_FOUND"
    assert data["error"]["details"] is None


def test_structured_error_envelope():
    """Verify structured HTTPException returns standard error envelope."""
    response = client.get("/test-structured-error")
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "SLOT_FULL"
    assert data["error"]["message"] == "This slot is full."


def test_unhandled_exception_no_stack_trace():
    """Verify 500 error returns envelope and hides stack traces."""
    response = client.get("/test-500")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert "secret stack trace" not in response.text
