"""Temporary hello-world app for verifying Railway deployment and storage."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import ADMIN_TOKEN
from app.db import get_connection, init_db, get_slots
from seed import seed_demo_slots


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Fail fast on missing admin secret and initialize SQLite in the mounted volume."""
    if not ADMIN_TOKEN:
        raise RuntimeError("ADMIN_TOKEN environment variable is unset or empty.")
    init_db()
    yield


app = FastAPI(
    title="Railway Deployment Smoke Test",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def hello_world() -> dict[str, str]:
    """Confirm the Railway service is reachable."""
    return {"message": "Hello from the Food Bank Volunteer Booking API."}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Check that SQLite can be opened on the configured storage path."""
    conn = get_connection()
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()
    return {"status": "ok"}


@app.post("/persistence-test")
def create_persistence_test_rows() -> dict[str, int]:
    """Create idempotent demo rows to verify persistence across redeploys."""
    inserted = seed_demo_slots()
    return {"inserted_rows": inserted, "total_slots": len(get_slots())}


@app.get("/persistence-test")
def check_persistence_test_rows() -> dict[str, int]:
    """Report persisted demo slots after a redeploy."""
    rows = get_slots()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No persisted rows found. POST /persistence-test first.",
        )
    return {"total_slots": len(rows)}
