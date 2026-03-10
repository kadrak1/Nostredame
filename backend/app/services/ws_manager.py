"""WebSocket connection manager — subscribe, broadcast, disconnect (T-062).

Two subscription namespaces:

* **order** — guest connections keyed by ``public_id``
  Used by :func:`routers.ws.ws_order_status`.
  Push updates via :meth:`ConnectionManager.broadcast_order_update`.

* **master** — admin/master connections keyed by ``venue_id``
  Used by :func:`routers.ws.ws_master_orders`.
  Push new-order events via :meth:`ConnectionManager.broadcast_to_master`.
  T-091 will add JWT auth to restrict this endpoint.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for order updates and master queue.

    Thread-safety: designed for a single-process async server (Uvicorn).
    All methods must be called from the same event loop.
    """

    def __init__(self) -> None:
        # public_id → set[WebSocket]
        self._order: dict[str, set[WebSocket]] = defaultdict(set)
        # venue_id → set[WebSocket]
        self._master: dict[int, set[WebSocket]] = defaultdict(set)

    # ------------------------------------------------------------------
    # Order subscriptions
    # ------------------------------------------------------------------

    async def connect_order(self, ws: WebSocket, public_id: str) -> None:
        """Accept WS and register it for order ``public_id``."""
        await ws.accept()
        self._order[public_id].add(ws)
        logger.info(
            "ws_order_connected",
            public_id=public_id,
            count=len(self._order[public_id]),
        )

    def disconnect_order(self, ws: WebSocket, public_id: str) -> None:
        """Remove WebSocket from order subscription."""
        self._order[public_id].discard(ws)
        if not self._order[public_id]:
            del self._order[public_id]
        logger.info("ws_order_disconnected", public_id=public_id)

    async def broadcast_order_update(
        self, public_id: str, payload: dict[str, Any]
    ) -> None:
        """Push ``payload`` to all clients subscribed to order ``public_id``.

        Dead connections (send raises) are silently removed.
        """
        sockets = list(self._order.get(public_id, set()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_order(ws, public_id)

    # ------------------------------------------------------------------
    # Master subscriptions
    # ------------------------------------------------------------------

    async def connect_master(self, ws: WebSocket, venue_id: int) -> None:
        """Accept WS and register master/admin for venue ``venue_id``."""
        await ws.accept()
        self._master[venue_id].add(ws)
        logger.info(
            "ws_master_connected",
            venue_id=venue_id,
            count=len(self._master[venue_id]),
        )

    def disconnect_master(self, ws: WebSocket, venue_id: int) -> None:
        """Remove WebSocket from master subscription."""
        self._master[venue_id].discard(ws)
        if not self._master[venue_id]:
            del self._master[venue_id]
        logger.info("ws_master_disconnected", venue_id=venue_id)

    async def broadcast_to_master(
        self, venue_id: int, payload: dict[str, Any]
    ) -> None:
        """Push ``payload`` to all master connections for venue ``venue_id``.

        Dead connections are silently removed.
        """
        sockets = list(self._master.get(venue_id, set()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_master(ws, venue_id)

    # ------------------------------------------------------------------
    # Introspection (used in tests and health checks)
    # ------------------------------------------------------------------

    def order_connection_count(self, public_id: str) -> int:
        """Return the number of active connections for order ``public_id``."""
        return len(self._order.get(public_id, set()))

    def master_connection_count(self, venue_id: int) -> int:
        """Return the number of active master connections for ``venue_id``."""
        return len(self._master.get(venue_id, set()))


# Singleton shared by all routers — import this, not the class.
ws_manager = ConnectionManager()
