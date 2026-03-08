"""Tobacco catalog router — CRUD for hookah tobaccos."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models.enums import UserRole
from app.models.tobacco import Tobacco
from app.schemas.tobacco import (
    TobaccoCreate,
    TobaccoPublic,
    TobaccoResponse,
    TobaccoUpdate,
)
from app.services.venue_helpers import ensure_venue_id, get_first_venue

router = APIRouter(prefix="/tobaccos", tags=["tobaccos"])

# Role alias — owner or admin
AdminOrOwner = Annotated[
    CurrentUser, Depends(require_role(UserRole.owner, UserRole.admin))
]


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------


@router.get("/public", response_model=list[TobaccoPublic])
async def list_tobaccos_public(
    db: Annotated[AsyncSession, Depends(get_db)],
    strength_min: Annotated[int | None, Query(ge=1, le=10)] = None,
    strength_max: Annotated[int | None, Query(ge=1, le=10)] = None,
) -> list[TobaccoPublic]:
    """Public — in-stock active tobaccos. Optional strength_min/strength_max filter (1–10)."""
    venue = await get_first_venue(db)
    stmt = (
        select(Tobacco)
        .where(
            Tobacco.venue_id == venue.id,
            Tobacco.is_active.is_(True),
            Tobacco.in_stock.is_(True),
        )
        .order_by(Tobacco.name)
    )
    if strength_min is not None and strength_max is not None and strength_min > strength_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="strength_min не может быть больше strength_max",
        )
    if strength_min is not None:
        stmt = stmt.where(Tobacco.strength >= strength_min)
    if strength_max is not None:
        stmt = stmt.where(Tobacco.strength <= strength_max)
    result = await db.execute(stmt)
    return [TobaccoPublic.model_validate(t) for t in result.scalars().all()]


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=list[TobaccoResponse])
async def list_tobaccos(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
    strength: Annotated[int | None, Query(ge=1, le=5)] = None,
    in_stock: bool | None = None,
    brand: str | None = None,
    flavor: str | None = None,
    include_inactive: bool = False,
) -> list[TobaccoResponse]:
    """List tobaccos with optional filters. Owner/admin only."""
    venue_id = ensure_venue_id(user)
    stmt = select(Tobacco).where(Tobacco.venue_id == venue_id)

    if not include_inactive:
        stmt = stmt.where(Tobacco.is_active.is_(True))
    if strength is not None:
        stmt = stmt.where(Tobacco.strength == strength)
    if in_stock is not None:
        stmt = stmt.where(Tobacco.in_stock.is_(in_stock))
    if brand:
        stmt = stmt.where(Tobacco.brand.ilike(f"%{brand}%"))
    if flavor:
        stmt = stmt.where(Tobacco.flavor_profile.like(f'%"{flavor}"%'))

    stmt = stmt.order_by(Tobacco.name)
    result = await db.execute(stmt)
    return [TobaccoResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/{tobacco_id}", response_model=TobaccoResponse)
async def get_tobacco(
    tobacco_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> TobaccoResponse:
    """Get a single tobacco by ID. Owner/admin only."""
    venue_id = ensure_venue_id(user)
    result = await db.execute(
        select(Tobacco).where(
            Tobacco.id == tobacco_id,
            Tobacco.venue_id == venue_id,
            Tobacco.is_active.is_(True),
        )
    )
    tobacco = result.scalar_one_or_none()
    if tobacco is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Табак не найден"
        )
    return TobaccoResponse.model_validate(tobacco)


@router.post("", response_model=TobaccoResponse, status_code=status.HTTP_201_CREATED)
async def create_tobacco(
    body: TobaccoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> TobaccoResponse:
    """Add a tobacco. Owner/admin only."""
    venue_id = ensure_venue_id(user)

    tobacco = Tobacco(venue_id=venue_id, **body.model_dump())
    db.add(tobacco)
    await db.flush()
    await db.refresh(tobacco)
    return TobaccoResponse.model_validate(tobacco)


@router.put("/{tobacco_id}", response_model=TobaccoResponse)
async def update_tobacco(
    tobacco_id: int,
    body: TobaccoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> TobaccoResponse:
    """Update a tobacco. Owner/admin only."""
    venue_id = ensure_venue_id(user)
    result = await db.execute(
        select(Tobacco).where(
            Tobacco.id == tobacco_id,
            Tobacco.venue_id == venue_id,
            Tobacco.is_active.is_(True),
        )
    )
    tobacco = result.scalar_one_or_none()
    if tobacco is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Табак не найден"
        )

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления",
        )

    for field, value in update_data.items():
        setattr(tobacco, field, value)

    await db.flush()
    await db.refresh(tobacco)
    return TobaccoResponse.model_validate(tobacco)


@router.delete("/{tobacco_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tobacco(
    tobacco_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> None:
    """Soft-delete a tobacco (set is_active=false). Owner/admin only."""
    venue_id = ensure_venue_id(user)
    result = await db.execute(
        select(Tobacco).where(
            Tobacco.id == tobacco_id,
            Tobacco.venue_id == venue_id,
            Tobacco.is_active.is_(True),
        )
    )
    tobacco = result.scalar_one_or_none()
    if tobacco is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Табак не найден"
        )
    tobacco.is_active = False
    await db.flush()
