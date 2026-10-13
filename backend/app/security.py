"""Admin authentication dependency for protected booking data."""

import hmac
import os

from fastapi import Header, HTTPException

from app.config import ADMIN_TOKEN


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Reject missing, incorrect, or unconfigured admin tokens."""
    expected = os.getenv("ADMIN_TOKEN", ADMIN_TOKEN).strip()
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(
            status_code=403,
            detail={"code": "UNAUTHORIZED", "message": "Admin access required."},
        )
