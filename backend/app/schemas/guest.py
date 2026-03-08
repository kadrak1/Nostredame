"""Pydantic schemas for guest authentication and profile endpoints."""

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator


_PHONE_RE = re.compile(r"^\+7\d{10}$")


class GuestLogin(BaseModel):
    phone: str = Field(..., min_length=12, max_length=12)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _PHONE_RE.match(v):
            raise ValueError("Телефон должен быть в формате +7XXXXXXXXXX")
        return v


class GuestLoginResponse(BaseModel):
    guest_id: int
    name: str
    is_new: bool


class GuestProfile(BaseModel):
    id: int
    name: str
    phone_masked: str
    first_visit: date
    total_bookings: int
    total_orders: int


class GuestUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
