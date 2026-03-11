"""Pydantic schemas for the hookah master panel (T-090)."""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import OrderSource, OrderStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strength_label(strength: int) -> str:
    """Human-readable label matching STRENGTH_LEVEL_RANGES (1-4/5-7/8-10)."""
    if strength <= 4:
        return "Лёгкий"
    if strength <= 7:
        return "Средний"
    return "Крепкий"


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MasterOrderItem(BaseModel):
    tobacco_name: str
    brand: str
    weight_grams: float


class MasterOrder(BaseModel):
    id: int
    public_id: str | None
    table_number: int
    strength: int
    strength_label: str
    notes: str
    status: OrderStatus
    source: OrderSource
    guest_name: str | None
    wait_seconds: int
    items: list[MasterOrderItem]
    created_at: datetime


class MasterOrderList(BaseModel):
    orders: list[MasterOrder]
    total: int


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class StatusUpdate(BaseModel):
    status: OrderStatus
