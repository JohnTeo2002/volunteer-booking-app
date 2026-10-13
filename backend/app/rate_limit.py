"""Shared SlowAPI limiter configured by app.config."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import DISABLE_RATE_LIMIT

limiter = Limiter(
    key_func=get_remote_address,
    enabled=not DISABLE_RATE_LIMIT,
)
