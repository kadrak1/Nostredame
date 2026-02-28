"""Venue router — public info + owner-only updates."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.venue import VenueDetail, VenuePublic, VenueUpdate
from app.services.venue_helpers import ensure_venue_id, get_first_venue, get_venue_by_id

router = APIRouter(prefix="/venue", tags=["venue"])


@router.get("", response_model=VenuePublic)
async def get_venue(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VenuePublic:
    """Public endpoint — return venue info without sensitive data."""
    venue = await get_first_venue(db)
    return VenuePublic.model_validate(venue)


@router.get("/detail", response_model=VenueDetail)
async def get_venue_detail(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
) -> VenueDetail:
    """Authenticated endpoint — full venue info for any authenticated user."""
    venue_id = ensure_venue_id(user)
    venue = await get_venue_by_id(db, venue_id=venue_id)
    return VenueDetail.model_validate(venue)


@router.put("", response_model=VenueDetail)
async def update_venue(
    body: VenueUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_role(UserRole.owner))],
) -> VenueDetail:
    """Update venue info — owner only.

    Omit a field to leave it unchanged.
    Send ``"working_hours": null`` to explicitly clear the schedule.
    """
    venue_id = ensure_venue_id(user)
    venue = await get_venue_by_id(db, venue_id=venue_id)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления",
        )

    # Convert working_hours Pydantic model → dict for JSON column
    if "working_hours" in update_data and update_data["working_hours"] is not None:
        update_data["working_hours"] = body.working_hours.model_dump(exclude_none=True)

    for field, value in update_data.items():
        setattr(venue, field, value)

    await db.flush()
    await db.refresh(venue)
    return VenueDetail.model_validate(venue)
