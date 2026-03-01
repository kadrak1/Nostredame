"""Pydantic schemas for Booking endpoints."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator

from app.models.enums import BookingStatus


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------

def _validate_phone(v: str) -> str:
    digits = "".join(c for c in v if c.isdigit())
    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Номер телефона должен содержать 10–15 цифр")
    return v.strip()


# ---------------------------------------------------------------------------
# Table availability
# ---------------------------------------------------------------------------

class AvailableTablesQuery(BaseModel):
    date: date
    time_from: time
    time_to: time
    guests: int = Field(..., ge=1, le=50)

    @field_validator("time_to")
    @classmethod
    def time_to_after_time_from(cls, v: time, info) -> time:
        time_from = info.data.get("time_from")
        if time_from and v <= time_from:
            raise ValueError("Время окончания должно быть позже начала")
        return v


class AvailableTableItem(BaseModel):
    """Table info for the booking flow (read-only floor plan)."""

    id: int
    number: int
    capacity: int
    x: float
    y: float
    width: float
    height: float
    shape: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Booking create / public / admin
# ---------------------------------------------------------------------------

class BookingCreate(BaseModel):
    table_id: int
    date: date
    time_from: time
    time_to: time
    guest_count: int = Field(..., ge=1, le=50)
    guest_name: str = Field(..., min_length=1, max_length=100)
    guest_phone: str = Field(..., description="Plaintext phone for hashing/encryption")
    notes: str = Field("", max_length=500)

    @field_validator("guest_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)

    @field_validator("time_to")
    @classmethod
    def time_to_after_time_from(cls, v: time, info) -> time:
        time_from = info.data.get("time_from")
        if time_from and v <= time_from:
            raise ValueError("Время окончания должно быть позже начала")
        return v


class BookingPublic(BaseModel):
    """Booking status for the guest (no sensitive data)."""

    id: int
    table_id: int
    date: date
    time_from: time
    time_to: time
    guest_count: int
    guest_name: str
    status: BookingStatus
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingAdmin(BaseModel):
    """Full booking info for admin panel."""

    id: int
    venue_id: int
    table_id: int
    guest_id: int | None
    date: date
    time_from: time
    time_to: time
    guest_count: int
    guest_name: str
    guest_phone_masked: str = ""   # populated by router
    status: BookingStatus
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Cancel / status check by phone
# ---------------------------------------------------------------------------

class PhoneVerify(BaseModel):
    guest_phone: str

    @field_validator("guest_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)
