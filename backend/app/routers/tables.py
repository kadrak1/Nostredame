"""Tables & Floor Plan router — CRUD for tables + floor plan management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models.enums import UserRole
from app.models.table import Table
from app.schemas.table import (
    FloorPlanResponse,
    FloorPlanUpdate,
    TableCreate,
    TablePublic,
    TableResponse,
    TableUpdate,
)
from app.services.venue_helpers import (
    ensure_venue_id,
    get_active_tables,
    get_first_venue,
    get_table_or_404,
)

router = APIRouter(tags=["tables"])

# Role alias — owner or admin
AdminOrOwner = Annotated[
    CurrentUser, Depends(require_role(UserRole.owner, UserRole.admin))
]


# ---------------------------------------------------------------------------
# Floor plan
# ---------------------------------------------------------------------------


@router.get("/venue/floor-plan", response_model=FloorPlanResponse)
async def get_floor_plan(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FloorPlanResponse:
    """Public — return floor plan with active tables."""
    venue = await get_first_venue(db)
    tables = await get_active_tables(db, venue.id)
    return FloorPlanResponse(
        floor_plan=venue.floor_plan,
        tables=[TablePublic.model_validate(t) for t in tables],
    )


@router.put("/venue/floor-plan", response_model=FloorPlanResponse)
async def update_floor_plan(
    body: FloorPlanUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> FloorPlanResponse:
    """Save floor plan decorations (walls, zones). Owner/admin only."""
    ensure_venue_id(user)
    # MVP: use first venue (consistent with GET)
    venue = await get_first_venue(db)
    venue.floor_plan = body.floor_plan
    await db.flush()
    await db.refresh(venue)

    tables = await get_active_tables(db, venue.id)
    return FloorPlanResponse(
        floor_plan=venue.floor_plan,
        tables=[TablePublic.model_validate(t) for t in tables],
    )


# ---------------------------------------------------------------------------
# Tables CRUD
# ---------------------------------------------------------------------------


@router.get("/tables", response_model=list[TableResponse])
async def list_tables(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
    include_inactive: bool = False,
) -> list[TableResponse]:
    """List all tables for the venue. Owner/admin only."""
    venue_id = ensure_venue_id(user)
    stmt = select(Table).where(Table.venue_id == venue_id)
    if not include_inactive:
        stmt = stmt.where(Table.is_active.is_(True))
    stmt = stmt.order_by(Table.number)
    result = await db.execute(stmt)
    return [TableResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/tables", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    body: TableCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> TableResponse:
    """Add a table. Owner/admin only."""
    venue_id = ensure_venue_id(user)

    table = Table(venue_id=venue_id, **body.model_dump())
    db.add(table)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Стол #{body.number} уже существует",
        )

    await db.refresh(table)
    return TableResponse.model_validate(table)


@router.put("/tables/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: int,
    body: TableUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> TableResponse:
    """Update a table. Owner/admin only."""
    venue_id = ensure_venue_id(user)
    table = await get_table_or_404(db, table_id, venue_id)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления",
        )

    for field, value in update_data.items():
        setattr(table, field, value)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Стол #{update_data.get('number', '?')} уже существует",
        )

    await db.refresh(table)
    return TableResponse.model_validate(table)


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> None:
    """Soft-delete a table (set is_active=false). Owner/admin only."""
    venue_id = ensure_venue_id(user)
    table = await get_table_or_404(db, table_id, venue_id)
    table.is_active = False
    await db.flush()
