"""Unit tests for Pydantic v2 schemas and validation rules."""

import pytest
from pydantic import ValidationError

from app.schemas import BookingRequest


def test_booking_request_valid():
    """Test valid booking request with trimming and normalization."""
    data = {
        "slot_id": 1,
        "volunteer_name": "  Jane Doe  ",
        "email": "  JANE.DOE@Example.COM  ",
        "phone": "  555-123-4567  ",
    }
    req = BookingRequest(**data)
    assert req.slot_id == 1
    assert req.volunteer_name == "Jane Doe"
    assert req.email == "jane.doe@example.com"
    assert req.phone == "555-123-4567"


@pytest.mark.parametrize(
    "slot_id",
    [0, -1, "1"],
)
def test_booking_request_invalid_slot_id(slot_id):
    """Test invalid slot_id values."""
    with pytest.raises(ValidationError):
        BookingRequest(
            slot_id=slot_id,
            volunteer_name="Jane",
            email="jane@example.com",
            phone="555-1234",
        )


@pytest.mark.parametrize(
    "name",
    ["", "   ", "a" * 101],
)
def test_booking_request_invalid_name(name):
    """Test invalid volunteer_name values (empty, whitespace-only, too long)."""
    with pytest.raises(ValidationError):
        BookingRequest(
            slot_id=1, volunteer_name=name, email="jane@example.com", phone="555-1234"
        )


@pytest.mark.parametrize(
    "email",
    # 64-char local part (the max), 3 valid 63-char labels, total 260 > 254
    [
        "not-an-email",
        "missing-at.com",
        "a" * 64 + "@" + ".".join(["a" * 63] * 3) + ".com",
    ],
)
def test_booking_request_invalid_email(email):
    """Test invalid email formats or lengths."""
    with pytest.raises(ValidationError):
        BookingRequest(slot_id=1, volunteer_name="Jane", email=email, phone="555-1234")


@pytest.mark.parametrize(
    "phone",
    ["123456", "123456789012345678901", "abc-defg", "555"],
)
def test_booking_request_invalid_phone(phone):
    """Test invalid phone numbers (too short, too long, insufficient digits, invalid chars)."""
    with pytest.raises(ValidationError):
        BookingRequest(
            slot_id=1, volunteer_name="Jane", email="jane@example.com", phone=phone
        )
