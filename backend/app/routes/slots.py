"""Public volunteer slot endpoints."""

import re
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BeforeValidator

from app.db import get_slots
from app.schemas import SlotResponse

router = APIRouter()


def validate_contract_date(value: object) -> date_type | None:
    """Require a real calendar date written exactly as YYYY-MM-DD."""
    if value is None:
        return None
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("Date must be in YYYY-MM-DD format.")
    try:
        return date_type.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Date must be in YYYY-MM-DD format.") from exc


ContractDate = Annotated[date_type | None, BeforeValidator(validate_contract_date)]


@router.get("/slots", response_model=list[SlotResponse])
def list_slots(
    event_id: Annotated[int | None, Query(gt=0)] = None,
    date: ContractDate = None,
) -> list[SlotResponse]:
    """List slots, optionally filtered by event ID and local date."""
    rows = get_slots(
        event_id=event_id,
        date=date.isoformat() if date is not None else None,
    )
    return [SlotResponse.model_validate(row) for row in rows]
