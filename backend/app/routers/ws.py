"""WebSocket endpoints for real-time order updates (T-062).

Endpoints
---------
``WS /ws/orders/{public_id}``
    Guest subscribes to status updates for their order.
    Protocol:
    * On connect → ``{"type": "status", "public_id": ..., "status": ...}``
    * On status change (pushed by ``ws_manager.broadcast_order_update``) →
      ``{"type": "status_update", "status": ...}``
    * Keepalive: server sends ``{"type": "ping"}`` every 25 s; client may
      reply ``{"type": "pong"}`` (not required).
    * Close code 4004 if order not found.

``WS /ws/master/orders?venue_id=<id>``
    Master / admin subscribes to the live order queue for a venue.
    Protocol:
    * On connect → ``{"type": "connected", "venue_id": ...}``
    * New order → ``{"type": "order.new", ...}``
    * Status change → ``{"type": "order.updated", ...}``
    NOTE: T-091 will replace ``?venue_id`` with JWT-based venue extraction.
"""
from __future__ import annotations

import asyncio
import json
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import HookahOrder
from app.services.ws_manager import ws_manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["websocket"])

# Keep-alive ping interval (seconds) — just under the typical 30 s idle timeout
_PING_INTERVAL = 25


# ---------------------------------------------------------------------------
# Helper: keepalive loop
# ---------------------------------------------------------------------------

async def _keepalive_loop(ws: WebSocket) -> None:
    """Wait for client messages; send server ping on timeout.

    Handles client ``{"type": "ping"}`` → replies ``{"type": "pong"}``.
    Raises :exc:`WebSocketDisconnect` when the client closes.
    Raises :exc:`Exception` if the server ping cannot be sent (broken pipe).
    Runs until the caller cancels or the client disconnects.
    """
    while True:
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=_PING_INTERVAL)
            try:
                msg = json.loads(raw)
                if isinstance(msg, dict) and msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except (json.JSONDecodeError, TypeError):
                pass
        except asyncio.TimeoutError:
            # No message received — send keepalive ping.
            # If send fails (socket closed between receive_text timeout and now),
            # propagate the exception so the caller's finally block runs.
            await ws.send_json({"type": "ping"})


# ---------------------------------------------------------------------------
# WS /ws/orders/{public_id}
# ---------------------------------------------------------------------------

@router.websocket("/ws/orders/{public_id}")
async def ws_order_status(
    websocket: WebSocket,
    public_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Subscribe to real-time status updates for order ``public_id``."""
    # Validate order exists *before* accepting the connection.
    # Must accept first — WebSocket handshake requires HTTP 101 before any close frame.
    result = await db.execute(
        select(HookahOrder).where(HookahOrder.public_id == public_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        await websocket.accept()
        await websocket.close(code=4004, reason="Order not found")
        return

    await ws_manager.connect_order(websocket, public_id)
    try:
        # Send initial status snapshot so the client doesn't have to poll
        await websocket.send_json(
            {
                "type": "status",
                "public_id": public_id,
                "status": order.status.value,
            }
        )
        await _keepalive_loop(websocket)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        # Guaranteed cleanup regardless of exception type (WebSocketDisconnect,
        # asyncio.CancelledError on server shutdown, broken-pipe RuntimeError, …)
        ws_manager.disconnect_order(websocket, public_id)


# ---------------------------------------------------------------------------
# WS /ws/master/orders?venue_id=<id>
# ---------------------------------------------------------------------------

@router.websocket("/ws/master/orders")
async def ws_master_orders(
    websocket: WebSocket,
    venue_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],  # noqa: ARG001 — reserved for T-091 auth
) -> None:
    """Subscribe master/admin to the live order queue for ``venue_id``.

    Query param ``venue_id`` is mandatory.
    T-091 will replace this with JWT-based venue_id extraction and auth guard.
    # TODO(T-091): validate venue exists in DB and extract venue_id from JWT.
    """
    await ws_manager.connect_master(websocket, venue_id)
    try:
        await websocket.send_json({"type": "connected", "venue_id": venue_id})
        await _keepalive_loop(websocket)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        # Guaranteed cleanup — handles CancelledError, RuntimeError, etc.
        ws_manager.disconnect_master(websocket, venue_id)
