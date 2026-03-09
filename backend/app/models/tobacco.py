"""Tobacco model — hookah tobacco catalog."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tobacco(Base):
    __tablename__ = "tobaccos"
    __table_args__ = (
        CheckConstraint("strength >= 1 AND strength <= 10", name="strength_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str] = mapped_column(String(100))
    strength: Mapped[int] = mapped_column(Integer)
    flavor_profile: Mapped[list | None] = mapped_column(JSON, nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    weight_available_grams: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    venue = relationship("Venue", back_populates="tobaccos")
