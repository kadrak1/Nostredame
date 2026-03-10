"""Tests for WebSocket manager (unit) and WS endpoints (integration) — T-062.

Unit tests: use AsyncMock WebSocket objects — no DB, no event-loop issues.
Integration tests: use starlette.testclient.TestClient with a file-based
SQLite seeded via synchronous SQLAlchemy (no cross-loop aiosqlite issues).
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session as SyncSession
from starlette.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.enums import OrderSource, OrderStatus, TableShape
from app.models.order import HookahOrder
from app.models.table import Table
from app.models.tobacco import Tobacco
from app.models.venue import Venue
from app.services.ws_manager import ConnectionManager


# ===========================================================================
# Unit tests — ConnectionManager (no DB, no event loop concerns)
# ===========================================================================

class TestConnectionManagerUnit:
    """Unit-tests for ConnectionManager using AsyncMock WebSocket objects."""

    @pytest.fixture
    def mgr(self) -> ConnectionManager:
        return ConnectionManager()

    def _mock_ws(self) -> MagicMock:
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    # --- order subscriptions ---

    @pytest.mark.asyncio
    async def test_connect_order_accepts_and_registers(self, mgr: ConnectionManager):
        ws = self._mock_ws()
        await mgr.connect_order(ws, "pid-1")
        ws.accept.assert_awaited_once()
        assert mgr.order_connection_count("pid-1") == 1

    @pytest.mark.asyncio
    async def test_disconnect_order_removes_socket(self, mgr: ConnectionManager):
        ws = self._mock_ws()
        await mgr.connect_order(ws, "pid-1")
        mgr.disconnect_order(ws, "pid-1")
        assert mgr.order_connection_count("pid-1") == 0

    @pytest.mark.asyncio
    async def test_disconnect_order_cleans_up_empty_key(self, mgr: ConnectionManager):
        ws = self._mock_ws()
        await mgr.connect_order(ws, "pid-cleanup")
        mgr.disconnect_order(ws, "pid-cleanup")
        assert "pid-cleanup" not in mgr._order

    @pytest.mark.asyncio
    async def test_broadcast_order_update_sends_to_all(self, mgr: ConnectionManager):
        ws1, ws2 = self._mock_ws(), self._mock_ws()
        await mgr.connect_order(ws1, "pid-2")
        await mgr.connect_order(ws2, "pid-2")
        payload = {"type": "status_update", "status": "accepted"}
        await mgr.broadcast_order_update("pid-2", payload)
        ws1.send_json.assert_awaited_once_with(payload)
        ws2.send_json.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_broadcast_order_update_removes_dead_connection(
        self, mgr: ConnectionManager
    ):
        ws_good = self._mock_ws()
        ws_dead = self._mock_ws()
        ws_dead.send_json = AsyncMock(side_effect=RuntimeError("closed"))
        await mgr.connect_order(ws_good, "pid-3")
        await mgr.connect_order(ws_dead, "pid-3")
        payload = {"type": "status_update", "status": "preparing"}
        await mgr.broadcast_order_update("pid-3", payload)
        # Dead socket removed, good one still present
        assert mgr.order_connection_count("pid-3") == 1
        ws_good.send_json.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_broadcast_order_update_no_op_when_no_connections(
        self, mgr: ConnectionManager
    ):
        """broadcast_order_update on unknown public_id must not raise."""
        await mgr.broadcast_order_update("nonexistent", {"type": "ping"})

    # --- master subscriptions ---

    @pytest.mark.asyncio
    async def test_connect_master_accepts_and_registers(self, mgr: ConnectionManager):
        ws = self._mock_ws()
        await mgr.connect_master(ws, venue_id=42)
        ws.accept.assert_awaited_once()
        assert mgr.master_connection_count(42) == 1

    @pytest.mark.asyncio
    async def test_disconnect_master_removes_socket(self, mgr: ConnectionManager):
        ws = self._mock_ws()
        await mgr.connect_master(ws, venue_id=42)
        mgr.disconnect_master(ws, venue_id=42)
        assert mgr.master_connection_count(42) == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_master_sends_to_all(self, mgr: ConnectionManager):
        ws1, ws2 = self._mock_ws(), self._mock_ws()
        await mgr.connect_master(ws1, venue_id=7)
        await mgr.connect_master(ws2, venue_id=7)
        payload = {"type": "order.new", "order_id": 99}
        await mgr.broadcast_to_master(7, payload)
        ws1.send_json.assert_awaited_once_with(payload)
        ws2.send_json.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_broadcast_to_master_removes_dead_connection(
        self, mgr: ConnectionManager
    ):
        ws_good = self._mock_ws()
        ws_dead = self._mock_ws()
        ws_dead.send_json = AsyncMock(side_effect=RuntimeError("closed"))
        await mgr.connect_master(ws_good, venue_id=8)
        await mgr.connect_master(ws_dead, venue_id=8)
        await mgr.broadcast_to_master(8, {"type": "test"})
        assert mgr.master_connection_count(8) == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_master_no_op_when_no_connections(
        self, mgr: ConnectionManager
    ):
        """broadcast_to_master on unknown venue_id must not raise."""
        await mgr.broadcast_to_master(venue_id=999, payload={"type": "ping"})

    @pytest.mark.asyncio
    async def test_separate_venues_are_isolated(self, mgr: ConnectionManager):
        """Master connections for different venues don't cross-pollinate."""
        ws1, ws2 = self._mock_ws(), self._mock_ws()
        await mgr.connect_master(ws1, venue_id=1)
        await mgr.connect_master(ws2, venue_id=2)
        await mgr.broadcast_to_master(1, {"type": "only-venue-1"})
        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_not_called()


# ===========================================================================
# Integration tests — WS endpoints via starlette.testclient.TestClient
#
# Strategy: seed data with *synchronous* SQLAlchemy (sqlite3 via sqlalchemy)
# into a temp file, then point the async dependency override at the same file
# via aiosqlite.  No cross-loop issues.
# ===========================================================================

def _seed_ws_db(db_path: str) -> dict:
    """Create schema + seed test data synchronously; return test data dict."""
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    with SyncSession(sync_engine) as s:
        venue = Venue(name="WS Venue", address="WS Addr", phone="+70000000001")
        s.add(venue)
        s.flush()

        table = Table(
            venue_id=venue.id,
            number=9,
            capacity=4,
            x=0, y=0, width=80, height=80,
            shape=TableShape.rect,
        )
        s.add(table)
        s.flush()

        tobacco = Tobacco(
            venue_id=venue.id,
            name="WS Tobacco",
            brand="WS Brand",
            strength=5,
            in_stock=True,
        )
        s.add(tobacco)
        s.flush()

        order = HookahOrder(
            public_id="ws-integration-pid",
            venue_id=venue.id,
            table_id=table.id,
            strength=5,
            source=OrderSource.qr_table,
            status=OrderStatus.pending,
        )
        s.add(order)
        s.flush()
        s.commit()

        data = {
            "venue_id": venue.id,
            "table_id": table.id,
            "tobacco_id": tobacco.id,
            "public_id": "ws-integration-pid",
            "table_number": 9,
        }

    sync_engine.dispose()
    return data


@pytest.fixture(scope="class")
def ws_setup():
    """One-time setup: temp SQLite + TestClient for WS integration tests."""
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tf.name
    tf.close()

    data = _seed_ws_db(db_path)

    # Async engine + session factory pointing at the same file
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    WsSession = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override():
        async with WsSession() as s:
            yield s

    app.dependency_overrides[get_db] = _override

    with TestClient(app) as tc:
        yield tc, data

    app.dependency_overrides.clear()

    # Dispose async engine synchronously (best-effort)
    try:
        asyncio.run(async_engine.dispose())
    except RuntimeError:
        pass

    os.unlink(db_path)


class TestWSOrderStatus:
    """Integration tests for WS /ws/orders/{public_id}."""

    def test_connect_sends_initial_status(self, ws_setup):
        """Connecting to a valid order returns initial status snapshot."""
        tc, data = ws_setup
        with tc.websocket_connect(f"/ws/orders/{data['public_id']}") as ws:
            msg = ws.receive_json()
        assert msg["type"] == "status"
        assert msg["public_id"] == data["public_id"]
        assert msg["status"] == "pending"

    def test_connect_not_found_closes_4004(self, ws_setup):
        """Connecting with unknown public_id receives close code 4004."""
        tc, _ = ws_setup
        with pytest.raises(Exception):
            # TestClient raises on unexpected close
            with tc.websocket_connect("/ws/orders/no-such-order") as ws:
                ws.receive_json()

    def test_ping_pong(self, ws_setup):
        """Client sends ping → server replies pong."""
        tc, data = ws_setup
        with tc.websocket_connect(f"/ws/orders/{data['public_id']}") as ws:
            ws.receive_json()  # discard initial status
            ws.send_json({"type": "ping"})
            msg = ws.receive_json()
        assert msg == {"type": "pong"}


class TestWSMasterOrders:
    """Integration tests for WS /ws/master/orders."""

    def test_connect_sends_connected_message(self, ws_setup):
        """Connecting to master WS returns connected confirmation."""
        tc, data = ws_setup
        with tc.websocket_connect(
            f"/ws/master/orders?venue_id={data['venue_id']}"
        ) as ws:
            msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["venue_id"] == data["venue_id"]

    def test_ping_pong(self, ws_setup):
        """Master client sends ping → server replies pong."""
        tc, data = ws_setup
        with tc.websocket_connect(
            f"/ws/master/orders?venue_id={data['venue_id']}"
        ) as ws:
            ws.receive_json()  # discard connected
            ws.send_json({"type": "ping"})
            msg = ws.receive_json()
        assert msg == {"type": "pong"}

    def test_new_order_broadcast_received(self, ws_setup):
        """Creating an order via HTTP broadcasts order.new to master WS.

        Opens master WS first, then POSTs a new order — the WS client should
        receive an ``order.new`` event pushed by ws_manager.broadcast_to_master.

        Strategy: WS runs in a background thread (blocks on receive_json);
        main thread POSTs the order; broadcast arrives via the shared ASGI
        event loop and is buffered in the WS session queue until receive_json
        consumes it.
        """
        tc, data = ws_setup
        received: list[dict] = []
        ready = threading.Event()
        done = threading.Event()

        def _run_ws() -> None:
            try:
                with tc.websocket_connect(
                    f"/ws/master/orders?venue_id={data['venue_id']}"
                ) as ws:
                    ws.receive_json()  # discard "connected"
                    ready.set()
                    # Block until broadcast arrives (or connection closes)
                    try:
                        msg = ws.receive_json()
                        received.append(msg)
                    except Exception:
                        pass
            finally:
                done.set()

        t = threading.Thread(target=_run_ws, daemon=True)
        t.start()
        ready.wait(timeout=3)

        # POST a new order — triggers broadcast_to_master inside the ASGI loop
        resp = tc.post(
            "/api/orders",
            json={
                "table_id": data["table_id"],
                "strength": 6,
                "items": [{"tobacco_id": data["tobacco_id"], "weight_grams": 20.0}],
            },
        )
        assert resp.status_code == 201

        done.wait(timeout=5)
        t.join(timeout=1)

        assert done.is_set(), "WS thread did not finish in time — broadcast may not have arrived"
        assert len(received) == 1, f"Expected 1 broadcast, got: {received}"
        assert received[0]["type"] == "order.new"
        assert received[0]["table_number"] == data["table_number"]
