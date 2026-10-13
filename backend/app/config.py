"""Configuration module.

The ONLY place environment variables are read.
"""

import os

# Read environment variables
ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "").strip()
CORS_ORIGINS_STR: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
DB_PATH: str = os.getenv("DB_PATH", "app.db")
DISABLE_RATE_LIMIT: bool = os.getenv("DISABLE_RATE_LIMIT", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
BOOKING_RATE_LIMIT: str = os.getenv("BOOKING_RATE_LIMIT", "10/minute")

# Fail fast at startup if ADMIN_TOKEN is unset or empty
if not ADMIN_TOKEN:
    raise RuntimeError("CRITICAL: ADMIN_TOKEN environment variable is unset or empty.")

# Parse CORS origins
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in CORS_ORIGINS_STR.split(",") if origin.strip()
]

if "*" in CORS_ORIGINS:
    raise RuntimeError(
        "CRITICAL: Wildcard CORS origin '*' is not allowed in deployed code."
    )
