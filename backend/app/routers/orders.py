"""Public orders router — QR-table order creation and status (T-061/T-062)."""

import uuid as uuid_lib
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.limiter import limiter
from app.models.enums import OrderSource, OrderStatus
from app.models.order import HookahOrder, OrderItem
from app.models.table import Table
from app.models.tobacco import Tobacco
from app.schemas.order import (
    OrderQRCreate,
    OrderQRPublic,
    OrderStatusItemPublic,
    OrderStatusPublic,
)
from app.services.ws_manager import ws_manager
from app.utils import get_client_ip

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["orders"])


# ---------------------------------------------------------------------------
# Rate limit key: client_ip + table_id (NFR-060-04)
# ---------------------------------------------------------------------------

async def _order_rl_key(request: Request) -> str:
    """Compose rate-limit key from client IP and table_id from request body.

    Using (IP + table_id) instead of IP-only so guests at different tables
    sharing the same venue Wi-Fi don't block each other.

    Relies on Starlette caching the body in request._body after the first
    `await request.json()` call — subsequent reads by FastAPI's Pydantic
    validation use the same cached bytes.  Fallback to IP-only when body
    is missing or not valid JSON.
    """
    try:
        body = await request.json()
        table_id = body.get("table_id", "x")
    except Exception:
        # Malformed / non-JSON body — fall back to IP-only key
        table_id = "x"
    return f"{get_client_ip(request)}:{table_id}"


# ---------------------------------------------------------------------------
# POST /api/orders — create a QR-table hookah order
# ---------------------------------------------------------------------------

@router.post("/orders", response_model=OrderQRPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/15minutes", key_func=_order_rl_key)
async def create_qr_order(
    request: Request,
    body: OrderQRCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderQRPublic:
    """Create a hookah order from a QR table scan.

    - Public endpoint (no auth required).
    - Rate-limited: 3 orders per 15 minutes per (IP + table_id).
    - ``source`` is always ``qr_table``.
    """
    # Validate table
    table = await db.get(Table, body.table_id)
    if not table or not table.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Стол не найден или неактивен",
        )

    # Validate tobaccos: must exist in the same venue, be active, and be in stock
    tobacco_ids = [item.tobacco_id for item in body.items]
    result = await db.execute(
        select(Tobacco).where(
            Tobacco.id.in_(tobacco_ids),
            Tobacco.venue_id == table.venue_id,
            Tobacco.is_active.is_(True),
        )
    )
    tobaccos: dict[int, Tobacco] = {t.id: t for t in result.scalars()}

    for tobacco_id in tobacco_ids:
        if tobacco_id not in tobaccos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Табак #{tobacco_id} не найден",
            )
        if not tobaccos[tobacco_id].in_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Табак «{tobaccos[tobacco_id].name}» нет в наличии",
            )

    # Create order
    public_id = str(uuid_lib.uuid4())
    order = HookahOrder(
        public_id=public_id,
        venue_id=table.venue_id,
        table_id=table.id,
        guest_name=body.guest_name,
        strength=body.strength,
        notes=body.notes,
        source=OrderSource.qr_table,
        status=OrderStatus.pending,
    )
    db.add(order)
    await db.flush()

    # Create items
    for item in body.items:
        db.add(OrderItem(
            order_id=order.id,
            tobacco_id=item.tobacco_id,
            weight_grams=item.weight_grams,
        ))

    await db.flush()
    await db.refresh(order)

    logger.info(
        "qr_order_created",
        order_id=order.id,
        public_id=order.public_id,
        table_id=table.id,
        table_number=table.number,
    )

    # Commit before broadcast so master clients can immediately query the new order
    # without hitting a "not found" race condition (T-062 code review HIGH #2).
    # get_db will call commit() again on exit — that's a no-op for an already-clean session.
    assert order.public_id is not None
    await db.commit()

    # Broadcast new order event to all master connections for this venue (T-062)
    await ws_manager.broadcast_to_master(
        table.venue_id,
        {
            "type": "order.new",
            "order_id": order.id,
            "public_id": order.public_id,
            "table_number": table.number,
            "strength": order.strength,
            "status": order.status.value,
        },
    )
    return OrderQRPublic(
        id=order.id,
        public_id=order.public_id,
        table_id=order.table_id,
        status=order.status,
        source=order.source,
        created_at=order.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/orders/{public_id}/status — public order status
# ---------------------------------------------------------------------------

@router.get("/orders/{public_id}/status", response_model=OrderStatusPublic)
async def get_order_status(
    public_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderStatusPublic:
    """Return current order status by public_id.

    Public endpoint — no auth required.
    Intended for the guest status page and WebSocket fallback polling.
    """
    result = await db.execute(
        select(HookahOrder)
        .where(HookahOrder.public_id == public_id)
        .options(
            joinedload(HookahOrder.items).joinedload(OrderItem.tobacco),
        )
    )
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден",
        )

    table = await db.get(Table, order.table_id)
    if table is None:
        # Table was hard-deleted — data integrity violation; log and fail loudly
        logger.error(
            "order_table_missing",
            order_id=order.id,
            table_id=order.table_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Данные заказа повреждены",
        )

    # order.public_id is guaranteed non-None for orders created post-T-061
    assert order.public_id is not None
    return OrderStatusPublic(
        public_id=order.public_id,
        status=order.status,
        table_number=table.number,
        strength=order.strength,
        items=[
            OrderStatusItemPublic(
                tobacco_name=item.tobacco.name,
                weight_grams=item.weight_grams,
            )
            for item in order.items
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
