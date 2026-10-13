"""Pydantic v2 request and response models."""

import re
from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PHONE_REGEX = r"^(?=(?:\D*\d){7})[0-9+() .-]{7,20}$"


class BookingRequest(BaseModel):
    """Request body for POST /book."""

    model_config = ConfigDict(str_strip_whitespace=True)

    slot_id: int = Field(gt=0, strict=True)
    volunteer_name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=254)
    phone: str = Field(max_length=20)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Trim and lowercase email before validation."""
        if not isinstance(v, str):
            return v
        return v.strip().lower()

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number against PHONE_REGEX."""
        if not isinstance(v, str):
            return v
        trimmed = v.strip()
        if not re.match(PHONE_REGEX, trimmed):
            raise ValueError(
                "Phone number must contain at least 7 digits and match allowed characters (7-20 characters)."
            )
        return trimmed


PathId = Annotated[int, Path(gt=0)]


class SlotResponse(BaseModel):
    """Public slot response; contains no volunteer personal information."""

    id: int = Field(ge=1)
    event_id: int = Field(ge=1)
    date: str
    start_time: str
    end_time: str
    capacity: int = Field(ge=1)
    booked: int = Field(ge=0)
    remaining: int = Field(ge=0)
