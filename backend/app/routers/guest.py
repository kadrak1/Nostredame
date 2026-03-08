"""Guest profile router — GET/PUT /api/guest/me."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentGuest
from app.models.booking import Booking
from app.models.order import HookahOrder
from app.schemas.guest import GuestProfile, GuestUpdate
from app.services.security import decrypt_phone, mask_phone

router = APIRouter(prefix="/guest", tags=["guest"])


async def _build_profile(guest, db: AsyncSession) -> GuestProfile:
    bookings_count = await db.scalar(
        select(func.count()).where(Booking.guest_id == guest.id)
    )
    orders_count = await db.scalar(
        select(func.count()).where(HookahOrder.guest_id == guest.id)
    )
    phone = decrypt_phone(guest.phone_encrypted)
    return GuestProfile(
        id=guest.id,
        name=guest.name,
        phone_masked=mask_phone(phone),
        first_visit=guest.created_at.date(),
        total_bookings=bookings_count or 0,
        total_orders=orders_count or 0,
    )


@router.get("/me", response_model=GuestProfile)
async def get_guest_me(
    guest: CurrentGuest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuestProfile:
    """Return the authenticated guest's profile."""
    return await _build_profile(guest, db)


@router.put("/me", response_model=GuestProfile)
async def update_guest_me(
    body: GuestUpdate,
    guest: CurrentGuest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuestProfile:
    """Update the authenticated guest's name."""
    guest.name = body.name
    await db.commit()
    await db.refresh(guest)
    return await _build_profile(guest, db)
