"""Table model — individual tables within a venue."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TableShape


class Table(Base):
    __tablename__ = "tables"
    __table_args__ = (
        UniqueConstraint("venue_id", "number", name="uq_table_venue_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    x: Mapped[float] = mapped_column(Float, default=0)
    y: Mapped[float] = mapped_column(Float, default=0)
    width: Mapped[float] = mapped_column(Float, default=80)
    height: Mapped[float] = mapped_column(Float, default=80)
    shape: Mapped[TableShape] = mapped_column(
        SAEnum(TableShape), default=TableShape.rect
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    venue = relationship("Venue", back_populates="tables")
    bookings = relationship("Booking", back_populates="table")
