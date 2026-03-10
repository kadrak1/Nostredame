"""Integration tests for POST /api/orders and GET /api/orders/{public_id}/status."""

import pytest
from httpx import AsyncClient


_ORDER_PAYLOAD = {
    "table_id": None,  # filled in each test
    "guest_name": "Алексей",
    "strength": 5,
    "notes": "Побольше дыма",
    "items": [{"tobacco_id": None, "weight_grams": 20.0}],
}


class TestCreateQROrder:
    @pytest.mark.asyncio
    async def test_create_order_success(
        self, client: AsyncClient, venue, table, tobacco
    ):
        """POST /api/orders returns 201 with public_id."""
        payload = {
            "table_id": table.id,
            "guest_name": "Дмитрий",
            "strength": 4,
            "notes": "Лёгкий",
            "items": [{"tobacco_id": tobacco.id, "weight_grams": 15.0}],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "public_id" in data
        assert len(data["public_id"]) > 0
        assert data["status"] == "pending"
        assert data["source"] == "qr_table"
        assert data["table_id"] == table.id

    @pytest.mark.asyncio
    async def test_create_order_no_guest_name(
        self, client: AsyncClient, venue, table, tobacco
    ):
        """guest_name is optional."""
        payload = {
            "table_id": table.id,
            "strength": 7,
            "items": [{"tobacco_id": tobacco.id, "weight_grams": 20.0}],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_order_table_not_found(
        self, client: AsyncClient, venue, tobacco
    ):
        """Non-existent table → 404."""
        payload = {
            "table_id": 9999,
            "strength": 5,
            "items": [{"tobacco_id": tobacco.id, "weight_grams": 20.0}],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_order_inactive_table(
        self, client: AsyncClient, venue, table, tobacco, admin_client: AsyncClient
    ):
        """Soft-deleted table → 404."""
        await admin_client.delete(f"/api/tables/{table.id}")
        payload = {
            "table_id": table.id,
            "strength": 5,
            "items": [{"tobacco_id": tobacco.id, "weight_grams": 20.0}],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_order_tobacco_not_found(
        self, client: AsyncClient, venue, table
    ):
        """Unknown tobacco_id → 404."""
        payload = {
            "table_id": table.id,
            "strength": 5,
            "items": [{"tobacco_id": 9999, "weight_grams": 20.0}],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_order_tobacco_out_of_stock(
        self, client: AsyncClient, venue, table, tobacco_out_of_stock
    ):
        """Out-of-stock tobacco → 400."""
        payload = {
            "table_id": table.id,
            "strength": 5,
            "items": [{"tobacco_id": tobacco_out_of_stock.id, "weight_grams": 20.0}],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_order_duplicate_tobaccos(
        self, client: AsyncClient, venue, table, tobacco
    ):
        """Duplicate tobacco_id in items → 422."""
        payload = {
            "table_id": table.id,
            "strength": 5,
            "items": [
                {"tobacco_id": tobacco.id, "weight_grams": 20.0},
                {"tobacco_id": tobacco.id, "weight_grams": 15.0},
            ],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_order_invalid_strength(
        self, client: AsyncClient, venue, table, tobacco
    ):
        """strength=11 → 422."""
        payload = {
            "table_id": table.id,
            "strength": 11,
            "items": [{"tobacco_id": tobacco.id, "weight_grams": 20.0}],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_order_no_items(
        self, client: AsyncClient, venue, table
    ):
        """Empty items list → 422."""
        payload = {
            "table_id": table.id,
            "strength": 5,
            "items": [],
        }
        resp = await client.post("/api/orders", json=payload)
        assert resp.status_code == 422


class TestOrderStatus:
    @pytest.mark.asyncio
    async def test_get_status_success(
        self, client: AsyncClient, venue, table, tobacco
    ):
        """GET /api/orders/{public_id}/status returns order details."""
        # Create order first
        payload = {
            "table_id": table.id,
            "guest_name": "Светлана",
            "strength": 3,
            "items": [{"tobacco_id": tobacco.id, "weight_grams": 25.0}],
        }
        create_resp = await client.post("/api/orders", json=payload)
        assert create_resp.status_code == 201
        public_id = create_resp.json()["public_id"]

        # Check status
        resp = await client.get(f"/api/orders/{public_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_id"] == public_id
        assert data["status"] == "pending"
        assert data["table_number"] == table.number
        assert data["strength"] == 3
        assert len(data["items"]) == 1
        assert data["items"][0]["tobacco_name"] == tobacco.name
        assert data["items"][0]["weight_grams"] == 25.0
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client: AsyncClient, venue):
        """Unknown public_id → 404."""
        resp = await client.get("/api/orders/nonexistent-uuid/status")
        assert resp.status_code == 404
