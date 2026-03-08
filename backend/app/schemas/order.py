"""Pydantic schemas for HookahOrder endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import OrderSource, OrderStatus
from app.schemas.validators import validate_phone


# ---------------------------------------------------------------------------
# Order item
# ---------------------------------------------------------------------------

class OrderItemCreate(BaseModel):
    tobacco_id: int
    weight_grams: float = Field(20.0, ge=5.0, le=40.0, description="Weight in grams (default 20 g per spec)")


class OrderItemPublic(BaseModel):
    id: int
    tobacco_id: int
    tobacco_name: str
    weight_grams: float

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_tobacco_name(cls, v: object) -> object:
        """Flatten tobacco relationship into tobacco_name when deserialising ORM objects."""
        if isinstance(v, dict):
            # Already a plain dict — tobacco_name must be present
            return v
        if hasattr(v, "tobacco"):
            tobacco = v.tobacco
            if tobacco is None:
                raise ValueError(
                    f"OrderItem(id={v.id}): relationship 'tobacco' is None — "
                    "use joinedload(OrderItem.tobacco) in the query."
                )
            return {
                "id": v.id,
                "tobacco_id": v.tobacco_id,
                "tobacco_name": tobacco.name,
                "weight_grams": v.weight_grams,
            }
        return v


# ---------------------------------------------------------------------------
# Order create / public
# ---------------------------------------------------------------------------

class OrderCreate(BaseModel):
    """Payload for POST /api/bookings/{id}/orders."""

    guest_phone: str = Field(..., description="Phone matching the booking — for ownership verification")
    strength: int = Field(..., ge=1, le=10, description="Hookah strength 1–10")
    notes: str = Field("", max_length=200)
    items: list[OrderItemCreate] = Field(..., min_length=1, max_length=3)

    @field_validator("guest_phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone(v)


class OrderPublic(BaseModel):
    """Response for guest-facing order endpoints."""

    id: int
    booking_id: int | None
    table_id: int
    strength: int
    status: OrderStatus
    source: OrderSource
    notes: str = ""
    items: list[OrderItemPublic]
    created_at: datetime

    model_config = {"from_attributes": True}
