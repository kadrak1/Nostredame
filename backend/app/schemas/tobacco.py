"""Pydantic schemas for Tobacco catalog endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TobaccoCreate(BaseModel):
    """Create a new tobacco entry."""

    name: str = Field(..., min_length=1, max_length=200, description="Tobacco name")
    brand: str = Field(..., min_length=1, max_length=100, description="Brand name")
    strength: int = Field(..., ge=1, le=10, description="Strength level 1-10")
    flavor_profile: list[str] | None = Field(
        None, description='Flavor tags, e.g. ["fruity", "mint"]'
    )
    in_stock: bool = Field(True, description="Whether currently in stock")
    weight_available_grams: int | None = Field(
        None, ge=0, description="Available weight in grams"
    )


class TobaccoUpdate(BaseModel):
    """Update an existing tobacco. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=200)
    brand: str | None = Field(None, min_length=1, max_length=100)
    strength: int | None = Field(None, ge=1, le=10)
    flavor_profile: list[str] | None = None
    in_stock: bool | None = None
    weight_available_grams: int | None = Field(None, ge=0)


class TobaccoResponse(BaseModel):
    """Full tobacco info returned to admin."""

    id: int
    venue_id: int
    name: str
    brand: str
    strength: int
    flavor_profile: list[str] | None
    in_stock: bool
    weight_available_grams: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TobaccoPublic(BaseModel):
    """Minimal tobacco info for guest-facing catalog (only in-stock items)."""

    id: int
    name: str
    brand: str
    strength: int
    flavor_profile: list[str] | None

    model_config = {"from_attributes": True}
