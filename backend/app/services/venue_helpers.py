"""Shared venue/table helpers used by multiple routers."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.table import Table
from app.models.venue import Venue


def ensure_venue_id(user) -> int:
    """Guard: ensure user is bound to a venue. Raises 400 if not."""
    if user.venue_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не привязан к заведению",
        )
    return user.venue_id


async def get_venue_by_id(db: AsyncSession, venue_id: int) -> Venue:
    """Fetch venue by id. Raises 404 if not found."""
    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    venue = result.scalar_one_or_none()
    if venue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заведение не найдено",
        )
    return venue


async def get_first_venue(db: AsyncSession) -> Venue:
    """Fetch the first venue (MVP: single-venue mode). Deterministic order."""
    result = await db.execute(select(Venue).order_by(Venue.id).limit(1))
    venue = result.scalar_one_or_none()
    if venue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заведение не найдено",
        )
    return venue


async def get_active_tables(db: AsyncSession, venue_id: int) -> list[Table]:
    """Fetch all active tables for a venue, ordered by number."""
    result = await db.execute(
        select(Table)
        .where(Table.venue_id == venue_id, Table.is_active.is_(True))
        .order_by(Table.number)
    )
    return list(result.scalars().all())


async def get_table_or_404(
    db: AsyncSession, table_id: int, venue_id: int
) -> Table:
    """Fetch a single active table, ensuring it belongs to the venue."""
    result = await db.execute(
        select(Table).where(
            Table.id == table_id,
            Table.venue_id == venue_id,
            Table.is_active.is_(True),
        )
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Стол не найден",
        )
    return table
