"""Public volunteer slot endpoints."""

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Query

from app.db import get_slots
from app.schemas import SlotResponse

router = APIRouter()


@router.get("/slots", response_model=list[SlotResponse])
def list_slots(
    event_id: Annotated[int | None, Query(gt=0)] = None,
    date: date_type | None = None,
) -> list[SlotResponse]:
    """List slots, optionally filtered by event ID and local date."""
    rows = get_slots(
        event_id=event_id,
        date=date.isoformat() if date is not None else None,
    )
    return [SlotResponse.model_validate(row) for row in rows]
