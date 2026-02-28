"""Guest model — customers who book and order."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    phone_encrypted: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(100), default="")
    telegram_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    bookings = relationship("Booking", back_populates="guest")
