"""Pydantic schemas for Table and Floor Plan endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TableShape


class TableCreate(BaseModel):
    """Create a new table."""

    number: int = Field(..., ge=1, description="Unique table number within venue")
    capacity: int = Field(..., ge=1, le=50, description="Max guests at this table")
    x: float = Field(0, ge=0, description="X coordinate on floor plan")
    y: float = Field(0, ge=0, description="Y coordinate on floor plan")
    width: float = Field(80, gt=0, description="Table width in px")
    height: float = Field(80, gt=0, description="Table height in px")
    shape: TableShape = Field(TableShape.rect, description="Table shape: rect or circle")


class TableUpdate(BaseModel):
    """Update an existing table. All fields optional."""

    number: int | None = Field(None, ge=1)
    capacity: int | None = Field(None, ge=1, le=50)
    x: float | None = Field(None, ge=0)
    y: float | None = Field(None, ge=0)
    width: float | None = Field(None, gt=0)
    height: float | None = Field(None, gt=0)
    shape: TableShape | None = None


class TableResponse(BaseModel):
    """Table info returned to client."""

    id: int
    venue_id: int
    number: int
    capacity: int
    x: float
    y: float
    width: float
    height: float
    shape: TableShape
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TablePublic(BaseModel):
    """Minimal table info for public floor plan view (guest-facing)."""

    id: int
    number: int
    capacity: int
    x: float
    y: float
    width: float
    height: float
    shape: TableShape

    model_config = {"from_attributes": True}


class TableInfoPublic(BaseModel):
    """Minimal public table info for the QR-landing page (T-063)."""

    id: int
    number: int
    venue_id: int
    venue_name: str

    model_config = {"from_attributes": True}


class FloorPlanResponse(BaseModel):
    """Full floor plan: venue metadata + tables + optional decorations."""

    floor_plan: dict | None = Field(
        None,
        description="JSON with walls, decorations, and other layout elements",
    )
    tables: list[TablePublic]


class FloorPlanUpdate(BaseModel):
    """Update floor plan decorations (walls, zones, etc.)."""

    floor_plan: dict = Field(
        ...,
        description="JSON with walls, decorations, and other layout elements",
    )
