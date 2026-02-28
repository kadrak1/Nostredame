"""Booking model — table reservations."""

from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BookingStatus


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_booking_conflict", "table_id", "date", "time_from", "time_to"),
        CheckConstraint("guest_count > 0", name="guest_count_positive"),
        CheckConstraint("time_from < time_to", name="time_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), index=True)
    guest_id: Mapped[int | None] = mapped_column(
        ForeignKey("guests.id"), nullable=True, index=True
    )
    guest_phone_encrypted: Mapped[str] = mapped_column(String(200))
    guest_name: Mapped[str] = mapped_column(String(100), default="")
    date: Mapped[date] = mapped_column(Date)
    time_from: Mapped[time] = mapped_column(Time)
    time_to: Mapped[time] = mapped_column(Time)
    guest_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus), default=BookingStatus.pending
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    table = relationship("Table", back_populates="bookings")
    guest = relationship("Guest", back_populates="bookings")
    orders = relationship("HookahOrder", back_populates="booking")
