"""Bookings router — public booking flow + admin management."""

import hmac as hmac_mod
from datetime import date as date_type, time as time_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.limiter import limiter
from app.models.booking import Booking
from app.models.enums import BookingStatus, UserRole
from app.models.guest import Guest
from app.models.table import Table
from app.schemas.booking import (
    AvailableTableItem,
    BookingAdmin,
    BookingCreate,
    BookingPublic,
    PhoneVerify,
)
from app.services.security import decrypt_phone, encrypt_phone, hash_phone, mask_phone
from app.services.venue_helpers import ensure_venue_id, get_first_venue

router = APIRouter(tags=["bookings"])

AdminOrOwner = Annotated[
    CurrentUser, Depends(require_role(UserRole.owner, UserRole.admin))
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _has_conflict(
    db: AsyncSession,
    table_id: int,
    booking_date: date_type,
    time_from: time_type,
    time_to: time_type,
    exclude_id: int | None = None,
) -> bool:
    """Return True if an active overlapping booking exists for the table."""
    stmt = select(Booking).where(
        Booking.table_id == table_id,
        Booking.date == booking_date,
        Booking.status.notin_([BookingStatus.cancelled]),
        Booking.time_from < time_to,
        Booking.time_to > time_from,
    )
    if exclude_id:
        stmt = stmt.where(Booking.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _upsert_guest(db: AsyncSession, phone: str, name: str) -> Guest:
    """Find existing guest by phone hash or create a new record."""
    phone_hash = hash_phone(phone)
    stmt = select(Guest).where(Guest.phone_hash == phone_hash)
    result = await db.execute(stmt)
    guest = result.scalar_one_or_none()

    if guest is None:
        guest = Guest(
            phone_hash=phone_hash,
            phone_encrypted=encrypt_phone(phone),
            name=name,
        )
        db.add(guest)
    elif name and guest.name != name:
        guest.name = name

    await db.flush()
    return guest


def _booking_to_admin(booking: Booking) -> BookingAdmin:
    """Convert Booking ORM → BookingAdmin schema with masked phone."""
    schema = BookingAdmin.model_validate(booking)
    try:
        plain = decrypt_phone(booking.guest_phone_encrypted)
        schema.guest_phone_masked = mask_phone(plain)
    except Exception:
        schema.guest_phone_masked = "***"
    return schema


def _parse_time(s: str) -> time_type:
    try:
        h, m = s.split(":")
        return time_type(int(h), int(m))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Формат времени: HH:MM",
        )


# ---------------------------------------------------------------------------
# Public: available tables
# ---------------------------------------------------------------------------

@router.get("/bookings/available-tables", response_model=list[AvailableTableItem])
async def get_available_tables(
    db: Annotated[AsyncSession, Depends(get_db)],
    booking_date: Annotated[date_type, Query(alias="date")],
    time_from: Annotated[str, Query()],
    time_to: Annotated[str, Query()],
    guests: Annotated[int, Query(ge=1, le=50)],
) -> list[AvailableTableItem]:
    """Public — return tables free for the requested date/time window."""
    t_from = _parse_time(time_from)
    t_to = _parse_time(time_to)

    if t_to <= t_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Время окончания должно быть позже начала",
        )

    venue = await get_first_venue(db)

    # IDs of tables with a conflicting active booking
    conflict_sub = select(Booking.table_id).where(
        Booking.venue_id == venue.id,
        Booking.date == booking_date,
        Booking.status.notin_([BookingStatus.cancelled]),
        Booking.time_from < t_to,
        Booking.time_to > t_from,
    )

    stmt = (
        select(Table)
        .where(
            Table.venue_id == venue.id,
            Table.is_active.is_(True),
            Table.capacity >= guests,
            Table.id.notin_(conflict_sub),
        )
        .order_by(Table.number)
    )

    result = await db.execute(stmt)
    return [AvailableTableItem.model_validate(t) for t in result.scalars().all()]


# ---------------------------------------------------------------------------
# Public: create booking (rate-limited)
# ---------------------------------------------------------------------------

@router.post(
    "/bookings",
    response_model=BookingPublic,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
async def create_booking(
    request: Request,
    body: BookingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingPublic:
    """Create a booking. Rate-limited: 5 per hour per IP."""
    venue = await get_first_venue(db)

    # Verify table belongs to venue
    table_stmt = select(Table).where(
        Table.id == body.table_id,
        Table.venue_id == venue.id,
        Table.is_active.is_(True),
    )
    table = (await db.execute(table_stmt)).scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Стол не найден")

    if table.capacity < body.guest_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Стол рассчитан на {table.capacity} гостей",
        )

    if await _has_conflict(db, body.table_id, body.date, body.time_from, body.time_to):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Стол уже забронирован на это время",
        )

    guest = await _upsert_guest(db, body.guest_phone, body.guest_name)

    booking = Booking(
        venue_id=venue.id,
        table_id=body.table_id,
        guest_id=guest.id,
        guest_phone_encrypted=encrypt_phone(body.guest_phone),
        guest_name=body.guest_name,
        date=body.date,
        time_from=body.time_from,
        time_to=body.time_to,
        guest_count=body.guest_count,
        status=BookingStatus.pending,
        notes=body.notes,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)
    return BookingPublic.model_validate(booking)


# ---------------------------------------------------------------------------
# Public: get booking status
# ---------------------------------------------------------------------------

@router.get("/bookings/{booking_id}", response_model=BookingPublic)
@limiter.limit("30/minute")
async def get_booking(
    request: Request,
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingPublic:
    """Public — get booking status by ID. Rate-limited to prevent enumeration."""
    stmt = select(Booking).where(Booking.id == booking_id)
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")
    return BookingPublic.model_validate(booking)


# ---------------------------------------------------------------------------
# Public: cancel (phone verification)
# ---------------------------------------------------------------------------

@router.put("/bookings/{booking_id}/cancel", response_model=BookingPublic)
@limiter.limit("10/minute")
async def cancel_booking(
    request: Request,
    booking_id: int,
    body: PhoneVerify,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingPublic:
    """Guest cancels their booking. Rate-limited to prevent phone brute-force."""
    stmt = select(Booking).where(Booking.id == booking_id)
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")

    if booking.status in (BookingStatus.cancelled, BookingStatus.completed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя отменить бронь со статусом '{booking.status.value}'",
        )

    # Verify ownership via phone hash
    guest_stmt = select(Guest).where(Guest.id == booking.guest_id)
    guest = (await db.execute(guest_stmt)).scalar_one_or_none()
    if guest is None or not hmac_mod.compare_digest(guest.phone_hash, hash_phone(body.guest_phone)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Номер телефона не совпадает",
        )

    booking.status = BookingStatus.cancelled
    await db.flush()
    await db.refresh(booking)
    return BookingPublic.model_validate(booking)


# ---------------------------------------------------------------------------
# Admin: list bookings
# ---------------------------------------------------------------------------

@router.get("/admin/bookings", response_model=list[BookingAdmin])
async def list_admin_bookings(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
    booking_date: Annotated[date_type | None, Query(alias="date")] = None,
    booking_status: Annotated[BookingStatus | None, Query(alias="status")] = None,
) -> list[BookingAdmin]:
    """Admin — list bookings with optional date/status filter."""
    venue_id = ensure_venue_id(user)

    stmt = select(Booking).where(Booking.venue_id == venue_id)
    if booking_date:
        stmt = stmt.where(Booking.date == booking_date)
    if booking_status:
        stmt = stmt.where(Booking.status == booking_status)
    stmt = stmt.order_by(Booking.date, Booking.time_from)

    result = await db.execute(stmt)
    return [_booking_to_admin(b) for b in result.scalars().all()]


# ---------------------------------------------------------------------------
# Admin: confirm / reject / complete
# ---------------------------------------------------------------------------

async def _get_admin_booking(db: AsyncSession, booking_id: int, venue_id: int) -> Booking:
    stmt = select(Booking).where(Booking.id == booking_id, Booking.venue_id == venue_id)
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")
    return booking


@router.put("/admin/bookings/{booking_id}/confirm", response_model=BookingAdmin)
async def confirm_booking(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> BookingAdmin:
    """Admin — confirm a pending booking."""
    booking = await _get_admin_booking(db, booking_id, ensure_venue_id(user))
    if booking.status != BookingStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя подтвердить бронь со статусом '{booking.status.value}'",
        )
    booking.status = BookingStatus.confirmed
    await db.flush()
    await db.refresh(booking)
    return _booking_to_admin(booking)


@router.put("/admin/bookings/{booking_id}/reject", response_model=BookingAdmin)
async def reject_booking(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> BookingAdmin:
    """Admin — reject (cancel) a booking."""
    booking = await _get_admin_booking(db, booking_id, ensure_venue_id(user))
    if booking.status in (BookingStatus.cancelled, BookingStatus.completed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя отклонить бронь со статусом '{booking.status.value}'",
        )
    booking.status = BookingStatus.cancelled
    await db.flush()
    await db.refresh(booking)
    return _booking_to_admin(booking)


@router.put("/admin/bookings/{booking_id}/complete", response_model=BookingAdmin)
async def complete_booking(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminOrOwner,
) -> BookingAdmin:
    """Admin — mark a confirmed booking as completed."""
    booking = await _get_admin_booking(db, booking_id, ensure_venue_id(user))
    if booking.status != BookingStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Завершить можно только подтверждённую бронь (статус: '{booking.status.value}')",
        )
    booking.status = BookingStatus.completed
    await db.flush()
    await db.refresh(booking)
    return _booking_to_admin(booking)
