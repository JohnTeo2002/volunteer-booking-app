"""Rate limiter configuration shared by public and admin routes."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Tests can explicitly disable throttling while exercising concurrent requests.
DISABLE_RATE_LIMIT = os.getenv("DISABLE_RATE_LIMIT", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

limiter = Limiter(
    key_func=get_remote_address,
    enabled=not DISABLE_RATE_LIMIT,
)
