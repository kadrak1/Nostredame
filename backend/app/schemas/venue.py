"""Pydantic schemas for Venue endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DayHours(BaseModel):
    """Working hours for a single day."""

    open: str = Field(
        ...,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        examples=["12:00"],
        description="Opening time in HH:MM format (00:00–23:59)",
    )
    close: str = Field(
        ...,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        examples=["02:00"],
        description="Closing time in HH:MM format (00:00–23:59)",
    )


class WorkingHours(BaseModel):
    """Weekly schedule — all days are optional (null = closed that day)."""

    mon: DayHours | None = None
    tue: DayHours | None = None
    wed: DayHours | None = None
    thu: DayHours | None = None
    fri: DayHours | None = None
    sat: DayHours | None = None
    sun: DayHours | None = None


class VenuePublic(BaseModel):
    """Public venue info — no sensitive fields."""

    id: int
    name: str
    address: str
    phone: str
    working_hours: WorkingHours | None = None

    model_config = {"from_attributes": True}


class VenueDetail(VenuePublic):
    """Full venue info for authenticated users (includes timestamps)."""

    created_at: datetime
    updated_at: datetime


class VenueUpdate(BaseModel):
    """Fields that an owner can update. All optional — partial update.

    - Omit a field to leave it unchanged.
    - Send ``"working_hours": null`` to explicitly clear the schedule.
    """

    name: str | None = Field(None, min_length=1, max_length=200)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=50)
    working_hours: WorkingHours | None = None
