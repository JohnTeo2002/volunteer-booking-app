"""Admin authentication dependency for protected booking data."""

import hmac

from fastapi import Header, HTTPException

from app import config


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Reject missing, incorrect, or unconfigured admin tokens."""
    expected = config.ADMIN_TOKEN
    if (
        not expected
        or not x_admin_token
        or not hmac.compare_digest(
            x_admin_token.encode("utf-8"), expected.encode("utf-8")
        )
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": "UNAUTHORIZED", "message": "Admin access required."},
        )
