"""Master recommendations router — CRUD (master/admin/owner) + public GET."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models.enums import UserRole
from app.models.master_recommendation import MasterRecommendation
from app.models.tobacco import Tobacco
from app.schemas.master_recommendation import (
    MasterRecommendationCreate,
    MasterRecommendationPublic,
    MasterRecommendationUpdate,
    StrengthLevel,
)
from app.services.venue_helpers import ensure_venue_id, get_first_venue

router = APIRouter(tags=["master_recommendations"])

MasterOrAdmin = Annotated[
    CurrentUser,
    Depends(require_role(UserRole.hookah_master, UserRole.admin, UserRole.owner)),
]

_MAX_ACTIVE_PER_VENUE = 10


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------


@router.get("/master/recommendations", response_model=list[MasterRecommendationPublic])
async def list_recommendations_public(
    db: Annotated[AsyncSession, Depends(get_db)],
    strength_level: Annotated[StrengthLevel | None, Query()] = None,
) -> list[MasterRecommendationPublic]:
    """Public — active recommendations, optionally filtered by strength_level."""
    venue = await get_first_venue(db)
    stmt = select(MasterRecommendation).where(
        MasterRecommendation.venue_id == venue.id,
        MasterRecommendation.is_active.is_(True),
    )
    if strength_level is not None:
        stmt = stmt.where(MasterRecommendation.strength_level == strength_level)
    stmt = stmt.order_by(MasterRecommendation.created_at.desc())
    result = await db.execute(stmt)
    return [MasterRecommendationPublic.model_validate(r) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# Staff CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/admin/master/recommendations", response_model=list[MasterRecommendationPublic]
)
async def list_recommendations_admin(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: MasterOrAdmin,
    strength_level: Annotated[StrengthLevel | None, Query()] = None,
    include_inactive: bool = False,
) -> list[MasterRecommendationPublic]:
    """Staff — list recommendations (includes inactive with include_inactive=true)."""
    venue_id = ensure_venue_id(user)
    stmt = select(MasterRecommendation).where(
        MasterRecommendation.venue_id == venue_id
    )
    if not include_inactive:
        stmt = stmt.where(MasterRecommendation.is_active.is_(True))
    if strength_level is not None:
        stmt = stmt.where(MasterRecommendation.strength_level == strength_level)
    stmt = stmt.order_by(MasterRecommendation.created_at.desc())
    result = await db.execute(stmt)
    return [MasterRecommendationPublic.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/master/recommendations",
    response_model=MasterRecommendationPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_recommendation(
    body: MasterRecommendationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: MasterOrAdmin,
) -> MasterRecommendationPublic:
    """Create a recommendation. hookah_master/admin/owner only."""
    venue_id = ensure_venue_id(user)

    # Validate tobaccos exist and belong to venue
    await _validate_tobacco_ids(db, [i.tobacco_id for i in body.items], venue_id)

    # Enforce max 10 active recommendations per venue (with row lock to avoid races)
    count_stmt = (
        select(func.count())
        .where(
            MasterRecommendation.venue_id == venue_id,
            MasterRecommendation.is_active.is_(True),
        )
        .with_for_update()
    )
    active_count = (await db.execute(count_stmt)).scalar_one()
    if active_count >= _MAX_ACTIVE_PER_VENUE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Нельзя иметь более {_MAX_ACTIVE_PER_VENUE} активных рекомендаций",
        )

    rec = MasterRecommendation(
        venue_id=venue_id,
        created_by=user.id,
        name=body.name,
        strength_level=body.strength_level,
        items=[item.model_dump() for item in body.items],
    )
    db.add(rec)
    await db.flush()
    await db.refresh(rec)
    return MasterRecommendationPublic.model_validate(rec)


@router.put(
    "/master/recommendations/{rec_id}",
    response_model=MasterRecommendationPublic,
)
async def update_recommendation(
    rec_id: int,
    body: MasterRecommendationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: MasterOrAdmin,
) -> MasterRecommendationPublic:
    """Update a recommendation. hookah_master/admin/owner only."""
    venue_id = ensure_venue_id(user)
    rec = await _get_rec(db, rec_id, venue_id)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления",
        )

    if "items" in update_data:
        await _validate_tobacco_ids(db, [i.tobacco_id for i in body.items], venue_id)  # type: ignore[union-attr]
        update_data["items"] = [item.model_dump() for item in body.items]  # type: ignore[union-attr]

    for field, value in update_data.items():
        setattr(rec, field, value)

    await db.flush()
    await db.refresh(rec)
    return MasterRecommendationPublic.model_validate(rec)


@router.delete(
    "/master/recommendations/{rec_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recommendation(
    rec_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: MasterOrAdmin,
) -> None:
    """Soft-delete a recommendation (set is_active=False). hookah_master/admin/owner only."""
    venue_id = ensure_venue_id(user)
    rec = await _get_rec(db, rec_id, venue_id)
    rec.is_active = False
    await db.flush()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _validate_tobacco_ids(
    db: AsyncSession, tobacco_ids: list[int], venue_id: int
) -> None:
    """Raise 400 if any tobacco_id is missing or doesn't belong to the venue."""
    found = {
        t.id
        for t in (
            await db.execute(
                select(Tobacco).where(
                    Tobacco.id.in_(tobacco_ids),
                    Tobacco.venue_id == venue_id,
                    Tobacco.is_active.is_(True),
                )
            )
        ).scalars().all()
    }
    missing = set(tobacco_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Табак(и) не найдены или не принадлежат заведению: {sorted(missing)}",
        )


async def _get_rec(
    db: AsyncSession, rec_id: int, venue_id: int
) -> MasterRecommendation:
    result = await db.execute(
        select(MasterRecommendation).where(
            MasterRecommendation.id == rec_id,
            MasterRecommendation.venue_id == venue_id,
            MasterRecommendation.is_active.is_(True),
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рекомендация не найдена",
        )
    return rec
