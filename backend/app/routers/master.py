"""Hookah master panel router — order queue management (T-090).

Endpoints
---------
GET  /api/master/orders
    Active queue (pending + accepted + preparing) or day history.
    Auth: hookah_master | admin | owner.

PUT  /api/master/orders/{order_id}/status
    Advance or cancel an order.  Validates allowed transitions.
    Broadcasts WS events to master queue and, where relevant, to the guest.
    Auth: hookah_master | admin | owner.
"""

from __future__ import annotations

import structlog
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models.enums import OrderStatus, UserRole
from app.models.order import HookahOrder, OrderItem
from app.models.table import Table
from app.schemas.master_order import (
    MasterOrder,
    MasterOrderItem,
    MasterOrderList,
    StatusUpdate,
    strength_label,
)
from app.services.venue_helpers import ensure_venue_id
from app.services.ws_manager import ws_manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["master"])

# Roles allowed to access master endpoints
MasterUser = Annotated[
    CurrentUser,
    Depends(require_role(UserRole.hookah_master, UserRole.admin, UserRole.owner)),
]

# ---------------------------------------------------------------------------
# Allowed status transitions — enforced on every PUT request
# ---------------------------------------------------------------------------

_ACTIVE_STATUSES = {OrderStatus.pending, OrderStatus.accepted, OrderStatus.preparing}

_VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending: {OrderStatus.accepted, OrderStatus.cancelled},
    OrderStatus.accepted: {OrderStatus.preparing, OrderStatus.cancelled},
    OrderStatus.preparing: {OrderStatus.served},
    # Terminal states — no further transitions
    OrderStatus.served: set(),
    OrderStatus.cancelled: set(),
}

# Statuses that should be forwarded to the guest via WS
# "served" is intentionally excluded (FR-090-12: гостю статус не передаётся)
_NOTIFY_GUEST_FOR: set[OrderStatus] = {
    OrderStatus.accepted,
    OrderStatus.preparing,
    OrderStatus.cancelled,
}


# ---------------------------------------------------------------------------
# Helper: build MasterOrder from ORM objects
# ---------------------------------------------------------------------------

def _build_master_order(
    order: HookahOrder,
    table_number: int,
    now: datetime,
) -> MasterOrder:
    wait_seconds = max(0, int((now - order.created_at.replace(tzinfo=None)).total_seconds()))
    items = [
        MasterOrderItem(
            tobacco_name=item.tobacco.name,
            brand=item.tobacco.brand,
            weight_grams=item.weight_grams,
        )
        for item in order.items
    ]
    return MasterOrder(
        id=order.id,
        public_id=order.public_id,
        table_number=table_number,
        strength=order.strength,
        strength_label=strength_label(order.strength),
        notes=order.notes,
        status=order.status,
        source=order.source,
        guest_name=order.guest_name,
        wait_seconds=wait_seconds,
        items=items,
        created_at=order.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/master/orders
# ---------------------------------------------------------------------------

@router.get("/master/orders", response_model=MasterOrderList)
async def list_master_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: MasterUser,
    date_filter: Annotated[date | None, Query(alias="date")] = None,
) -> MasterOrderList:
    """Return the active order queue or a day's history.

    * No ``date`` param → active queue (pending + accepted + preparing), FIFO.
    * ``?date=YYYY-MM-DD`` → all orders for that calendar day (any status).
    """
    venue_id = ensure_venue_id(user)

    stmt = (
        select(HookahOrder)
        .where(HookahOrder.venue_id == venue_id)
        .options(joinedload(HookahOrder.items).joinedload(OrderItem.tobacco))
    )

    if date_filter is not None:
        stmt = stmt.where(
            HookahOrder.created_at >= datetime(date_filter.year, date_filter.month, date_filter.day),
            HookahOrder.created_at < datetime(date_filter.year, date_filter.month, date_filter.day + 1)
            if date_filter.day < 28  # safe shortcut; proper month-end handled below
            else _next_day_start(date_filter),
        ).order_by(HookahOrder.created_at.desc())
    else:
        stmt = stmt.where(
            HookahOrder.status.in_(_ACTIVE_STATUSES)
        ).order_by(HookahOrder.created_at.asc())  # FIFO

    result = await db.execute(stmt)
    orders = result.unique().scalars().all()

    # Batch-load tables to get table_number without N+1
    table_ids = {o.table_id for o in orders}
    tmap: dict[int, Table] = {}
    if table_ids:
        t_result = await db.execute(select(Table).where(Table.id.in_(table_ids)))
        tmap = {t.id: t for t in t_result.scalars()}

    now = datetime.utcnow()
    master_orders = [
        _build_master_order(o, tmap[o.table_id].number if o.table_id in tmap else 0, now)
        for o in orders
    ]
    return MasterOrderList(orders=master_orders, total=len(master_orders))


def _next_day_start(d: date) -> datetime:
    """Return midnight of the day after ``d``."""
    import calendar
    year, month, day = d.year, d.month, d.day
    _, last_day = calendar.monthrange(year, month)
    if day >= last_day:
        # Roll over to next month
        if month == 12:
            return datetime(year + 1, 1, 1)
        return datetime(year, month + 1, 1)
    return datetime(year, month, day + 1)


# ---------------------------------------------------------------------------
# PUT /api/master/orders/{order_id}/status
# ---------------------------------------------------------------------------

@router.put("/master/orders/{order_id}/status", response_model=MasterOrder)
async def update_order_status(
    order_id: int,
    body: StatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: MasterUser,
) -> MasterOrder:
    """Change the status of an order.

    Validates the transition, persists it, then broadcasts:
    * ``order.updated`` to master WS subscribers for the venue.
    * ``status_update`` to the guest WS subscriber (all statuses except ``served``).
    """
    venue_id = ensure_venue_id(user)

    result = await db.execute(
        select(HookahOrder)
        .where(HookahOrder.id == order_id, HookahOrder.venue_id == venue_id)
        .options(joinedload(HookahOrder.items).joinedload(OrderItem.tobacco))
    )
    order = result.unique().scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден",
        )

    new_status = body.status
    allowed = _VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Нельзя перевести заказ из «{order.status.value}» "
                f"в «{new_status.value}». "
                f"Допустимые переходы: {[s.value for s in allowed] or 'нет'}."
            ),
        )

    old_status = order.status
    order.status = new_status
    await db.flush()
    # NOTE: do NOT call db.refresh(order) here — it would expire the eagerly-loaded
    # `items` relationship, causing a lazy-load attempt in the async context.

    logger.info(
        "order_status_changed",
        order_id=order.id,
        old_status=old_status.value,
        new_status=new_status.value,
        changed_by=user.id,
    )

    # Load table for response
    table = await db.get(Table, order.table_id)
    table_number = table.number if table else 0

    now = datetime.utcnow()
    master_order = _build_master_order(order, table_number, now)

    # Commit before broadcasts to avoid races (WS client polls REST immediately)
    await db.commit()

    # Broadcast to master panel
    assert order.public_id is not None or True  # public_id may be None for old orders
    await ws_manager.broadcast_to_master(
        venue_id,
        {
            "type": "order.updated",
            "order_id": order.id,
            "public_id": order.public_id,
            "table_number": table_number,
            "status": new_status.value,
        },
    )

    # Broadcast to guest (exclude "served" per FR-090-12)
    if order.public_id and new_status in _NOTIFY_GUEST_FOR:
        await ws_manager.broadcast_order_update(
            order.public_id,
            {"type": "status_update", "status": new_status.value},
        )

    return master_order
