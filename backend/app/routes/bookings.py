"""Public booking endpoint and domain-error to HTTP mapping."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from app.config import BOOKING_RATE_LIMIT
from app.db import DuplicateBooking, SlotFull, SlotNotFound, create_booking
from app.rate_limit import limiter
from app.schemas import BookingRequest, BookingResponse

router = APIRouter()


@router.post("/book", response_model=BookingResponse, status_code=201)
@limiter.limit(BOOKING_RATE_LIMIT)
def book_slot(request: Request, booking: BookingRequest) -> BookingResponse:
    """Atomically create a booking and return the contract response."""
    try:
        result = create_booking(
            slot_id=booking.slot_id,
            volunteer_name=booking.volunteer_name,
            email=str(booking.email),
            phone=booking.phone,
        )
    except SlotNotFound:
        raise HTTPException(
            status_code=404,
            detail={"code": "SLOT_NOT_FOUND", "message": "Slot not found."},
        ) from None
    except SlotFull:
        raise HTTPException(
            status_code=409,
            detail={"code": "SLOT_FULL", "message": "This slot is full."},
        ) from None
    except DuplicateBooking:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DUPLICATE_BOOKING",
                "message": "You have already booked this slot.",
            },
        ) from None

    # SQLite CURRENT_TIMESTAMP is UTC but lacks the ISO 8601 T and Z markers.
    timestamp = datetime.strptime(str(result["created_at"]), "%Y-%m-%d %H:%M:%S")
    result["created_at"] = (
        timestamp.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
    )
    return BookingResponse.model_validate(result)
