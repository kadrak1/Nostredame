"""Hookah order models — orders and their tobacco items."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import OrderSource, OrderStatus


class HookahOrder(Base):
    __tablename__ = "hookah_orders"
    __table_args__ = (
        CheckConstraint("strength >= 1 AND strength <= 10", name="strength_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), index=True)
    guest_id: Mapped[int | None] = mapped_column(
        ForeignKey("guests.id"), nullable=True, index=True
    )
    strength: Mapped[int] = mapped_column(Integer)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.pending
    )
    source: Mapped[OrderSource] = mapped_column(
        SAEnum(OrderSource),
        default=OrderSource.booking_preorder,
        server_default=OrderSource.booking_preorder.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    booking = relationship("Booking", back_populates="orders")
    guest = relationship("Guest")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("hookah_orders.id"), index=True
    )
    tobacco_id: Mapped[int] = mapped_column(ForeignKey("tobaccos.id"), index=True)
    weight_grams: Mapped[float] = mapped_column(Float, default=15.0)

    order = relationship("HookahOrder", back_populates="items")
