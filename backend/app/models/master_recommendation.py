"""MasterRecommendation model — hookah master's curated mixes."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MasterRecommendation(Base):
    __tablename__ = "master_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    # "light" (1-4) | "medium" (5-7) | "strong" (8-10)
    strength_level: Mapped[str] = mapped_column(String(10))
    # JSON list: [{"tobacco_id": int, "weight_grams": float}]
    items: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    venue = relationship("Venue")
    creator = relationship("User")
