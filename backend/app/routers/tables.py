"""Tables & Floor Plan router — CRUD for tables + floor plan management."""

import io
import zipfile
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models.enums import UserRole
from app.models.table import Table
from app.models.venue import Venue
from app.schemas.table import (
    FloorPlanResponse,
    FloorPlanUpdate,
    TableCreate,
    TableInfoPublic,
    TablePublic,
    TableResponse,
    TableUpdate,
)
from app.services.qr_generator import generate_qr_png
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


# ---------------------------------------------------------------------------
# Public table info — for QR landing page (T-063)
# ---------------------------------------------------------------------------


@router.get("/tables/{table_id}/info", response_model=TableInfoPublic)
async def get_table_info(
    table_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TableInfoPublic:
    """Return minimal public table info for the QR-landing page.

    Public endpoint — no auth required.
    Returns 404 if the table doesn't exist or is inactive.
    """
    table = await db.get(Table, table_id)
    if not table or not table.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Стол не найден или неактивен",
        )
    venue = await db.get(Venue, table.venue_id)
    if venue is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Данные заведения повреждены",
        )
    return TableInfoPublic(
        id=table.id,
        number=table.number,
        venue_id=table.venue_id,
        venue_name=venue.name,
    )


# ---------------------------------------------------------------------------
# QR code generation (admin/owner only)
# ---------------------------------------------------------------------------


@router.get("/tables/qr-all")
async def get_all_qr_codes(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
    size: Annotated[int, Query(ge=100, le=2000)] = 300,
) -> Response:
    """Download a ZIP archive containing QR-code PNGs for all active tables.

    Each file is named ``table_{number}.png``.
    Owner/admin only.
    """
    venue_id = ensure_venue_id(user)
    stmt = (
        select(Table)
        .where(Table.venue_id == venue_id, Table.is_active.is_(True))
        .order_by(Table.number)
    )
    tables = (await db.execute(stmt)).scalars().all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for table in tables:
            url = f"https://{settings.domain}/table/{table.id}"
            zf.writestr(f"table_{table.number}.png", generate_qr_png(url, size))

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="qr-codes.zip"'},
    )


@router.get("/tables/{table_id}/qr")
async def get_table_qr(
    table_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
    size: Annotated[int, Query(ge=100, le=2000)] = 300,
) -> Response:
    """Download a QR-code PNG for a specific table.

    The QR encodes ``https://{domain}/table/{table_id}``.
    Owner/admin only.
    """
    venue_id = ensure_venue_id(user)
    table = await get_table_or_404(db, table_id, venue_id)

    url = f"https://{settings.domain}/table/{table.id}"
    png_bytes = generate_qr_png(url, size)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="table_{table.number}.png"'
        },
    )
