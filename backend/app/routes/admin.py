"""Admin-only booking lookup endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from app.config import BOOKING_RATE_LIMIT
from app.db import get_booking
from app.rate_limit import limiter
from app.schemas import BookingResponse
from app.security import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/{id}", response_model=BookingResponse)
@limiter.limit(BOOKING_RATE_LIMIT)
def get_booking_route(
    request: Request, id: Annotated[int, Path(gt=0)]
) -> BookingResponse:
    """Return a booking by ID to an authenticated administrator."""
    booking = get_booking(id)
    if booking is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "BOOKING_NOT_FOUND", "message": "Booking not found."},
        )
    timestamp = datetime.strptime(
        str(booking["created_at"]), "%Y-%m-%d %H:%M:%S"
    )
    booking["created_at"] = timestamp.replace(tzinfo=UTC).isoformat().replace(
        "+00:00", "Z"
    )
    return BookingResponse.model_validate(booking)
