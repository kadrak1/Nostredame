"""Integration tests for /api/master/orders endpoints (T-090)."""

import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrderSource, OrderStatus
from app.models.order import HookahOrder, OrderItem


# ---------------------------------------------------------------------------
# Shared fixture: a pending order seeded in DB
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def pending_order(
    db_session: AsyncSession, venue, table, tobacco
) -> HookahOrder:
    """Create a pending hookah order with one item."""
    order = HookahOrder(
        venue_id=venue.id,
        table_id=table.id,
        public_id=str(uuid.uuid4()),
        strength=5,
        notes="тестовые заметки",
        status=OrderStatus.pending,
        source=OrderSource.qr_table,
        guest_name="Тест Гость",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(order_id=order.id, tobacco_id=tobacco.id, weight_grams=25.0)
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(order)
    return order


@pytest_asyncio.fixture
async def served_order(
    db_session: AsyncSession, venue, table, tobacco
) -> HookahOrder:
    """Create a terminal (served) order."""
    order = HookahOrder(
        venue_id=venue.id,
        table_id=table.id,
        public_id=str(uuid.uuid4()),
        strength=3,
        notes="",
        status=OrderStatus.served,
        source=OrderSource.qr_table,
        guest_name=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(order)
    await db_session.flush()
    await db_session.refresh(order)
    return order


# ---------------------------------------------------------------------------
# GET /api/master/orders
# ---------------------------------------------------------------------------


class TestListMasterOrders:
    @pytest.mark.asyncio
    async def test_active_queue_empty(self, master_client: AsyncClient, venue):
        """No orders → empty list."""
        resp = await master_client.get("/api/master/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["orders"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_active_queue_shows_pending_order(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Pending order appears in active queue."""
        resp = await master_client.get("/api/master/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        order = data["orders"][0]
        assert order["id"] == pending_order.id
        assert order["status"] == "pending"
        assert order["strength"] == 5
        assert order["guest_name"] == "Тест Гость"
        assert order["table_number"] == 1
        assert len(order["items"]) == 1
        assert order["items"][0]["weight_grams"] == 25.0
        assert "strength_label" in order
        assert "wait_seconds" in order

    @pytest.mark.asyncio
    async def test_active_queue_excludes_served(
        self, master_client: AsyncClient, venue, served_order
    ):
        """Served (terminal) orders are excluded from active queue."""
        resp = await master_client.get("/api/master/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_date_filter_returns_served(
        self, master_client: AsyncClient, venue, served_order
    ):
        """Date filter includes all statuses for that day."""
        today = served_order.created_at.strftime("%Y-%m-%d")
        resp = await master_client.get(f"/api/master/orders?date={today}")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()["orders"]]
        assert served_order.id in ids

    @pytest.mark.asyncio
    async def test_date_filter_different_day_empty(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Date filter for a different day returns empty."""
        resp = await master_client.get("/api/master/orders?date=2020-01-01")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client: AsyncClient, venue):
        """Unauthenticated request returns 401."""
        resp = await client.get("/api/master/orders")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_date_param(self, master_client: AsyncClient, venue):
        """Invalid date format returns 422."""
        resp = await master_client.get("/api/master/orders?date=not-a-date")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_strength_label_light(
        self, master_client: AsyncClient, venue, db_session, table, tobacco
    ):
        """Strength ≤4 gets label 'Лёгкий'."""
        order = HookahOrder(
            venue_id=venue.id, table_id=table.id, public_id=str(uuid.uuid4()),
            strength=2, notes="", status=OrderStatus.pending,
            source=OrderSource.qr_table, guest_name=None,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db_session.add(order)
        item = OrderItem(order_id=None, tobacco_id=tobacco.id, weight_grams=20.0)
        db_session.add(order)
        await db_session.flush()
        item.order_id = order.id
        db_session.add(item)
        await db_session.flush()

        resp = await master_client.get("/api/master/orders")
        orders = resp.json()["orders"]
        o = next(x for x in orders if x["id"] == order.id)
        assert o["strength_label"] == "Лёгкий"

    @pytest.mark.asyncio
    async def test_strength_label_medium(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Strength 5-7 gets label 'Средний'."""
        resp = await master_client.get("/api/master/orders")
        orders = resp.json()["orders"]
        o = next(x for x in orders if x["id"] == pending_order.id)
        assert o["strength_label"] == "Средний"  # strength=5


# ---------------------------------------------------------------------------
# PUT /api/master/orders/{order_id}/status
# ---------------------------------------------------------------------------


class TestUpdateOrderStatus:
    @pytest.mark.asyncio
    async def test_pending_to_accepted(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Valid transition pending → accepted."""
        resp = await master_client.put(
            f"/api/master/orders/{pending_order.id}/status",
            json={"status": "accepted"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["id"] == pending_order.id

    @pytest.mark.asyncio
    async def test_pending_to_cancelled(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Valid transition pending → cancelled."""
        resp = await master_client.put(
            f"/api/master/orders/{pending_order.id}/status",
            json={"status": "cancelled"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_accepted_to_preparing(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Chain: pending → accepted → preparing."""
        await master_client.put(
            f"/api/master/orders/{pending_order.id}/status",
            json={"status": "accepted"},
        )
        resp = await master_client.put(
            f"/api/master/orders/{pending_order.id}/status",
            json={"status": "preparing"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "preparing"

    @pytest.mark.asyncio
    async def test_preparing_to_served(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Full chain pending → accepted → preparing → served."""
        for s in ("accepted", "preparing", "served"):
            resp = await master_client.put(
                f"/api/master/orders/{pending_order.id}/status",
                json={"status": s},
            )
            assert resp.status_code == 200
        assert resp.json()["status"] == "served"

    @pytest.mark.asyncio
    async def test_invalid_transition_pending_to_served(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Invalid jump pending → served returns 400."""
        resp = await master_client.put(
            f"/api/master/orders/{pending_order.id}/status",
            json={"status": "served"},
        )
        assert resp.status_code == 400
        assert "pending" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_transition_served_to_accepted(
        self, master_client: AsyncClient, venue, served_order
    ):
        """Terminal state: served → accepted is forbidden."""
        resp = await master_client.put(
            f"/api/master/orders/{served_order.id}/status",
            json={"status": "accepted"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_order_not_found(self, master_client: AsyncClient, venue):
        """Non-existent order returns 404."""
        resp = await master_client.put(
            "/api/master/orders/99999/status",
            json={"status": "accepted"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_status_value(
        self, master_client: AsyncClient, venue, pending_order
    ):
        """Unknown status string returns 422."""
        resp = await master_client.put(
            f"/api/master/orders/{pending_order.id}/status",
            json={"status": "flying"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client: AsyncClient, venue, pending_order):
        """Unauthenticated request returns 401."""
        resp = await client.put(
            f"/api/master/orders/{pending_order.id}/status",
            json={"status": "accepted"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_venue_isolation(
        self,
        master_client: AsyncClient,
        db_session: AsyncSession,
        pending_order,
    ):
        """Cannot change status of an order from a different venue."""
        # Create a second venue and its order
        from app.models.venue import Venue
        from app.models.table import Table
        from app.models.enums import TableShape

        venue2 = Venue(name="Other Venue", address="Other St", phone="+70000000000")
        db_session.add(venue2)
        await db_session.flush()

        table2 = Table(
            venue_id=venue2.id, number=1, capacity=4,
            x=0, y=0, width=80, height=80, shape=TableShape.rect,
        )
        db_session.add(table2)
        await db_session.flush()

        other_order = HookahOrder(
            venue_id=venue2.id, table_id=table2.id,
            public_id=str(uuid.uuid4()),
            strength=3, notes="", status=OrderStatus.pending,
            source=OrderSource.qr_table, guest_name=None,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db_session.add(other_order)
        await db_session.flush()

        # master_client belongs to venue 1 — should get 404 for venue 2's order
        resp = await master_client.put(
            f"/api/master/orders/{other_order.id}/status",
            json={"status": "accepted"},
        )
        assert resp.status_code == 404
