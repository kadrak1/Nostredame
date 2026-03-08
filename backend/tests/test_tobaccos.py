"""Integration tests for /api/tobaccos endpoints."""

import pytest
from httpx import AsyncClient


class TestTobaccosPublic:
    @pytest.mark.asyncio
    async def test_public_only_in_stock(
        self, client: AsyncClient, venue, tobacco, tobacco_out_of_stock
    ):
        resp = await client.get("/api/tobaccos/public")
        assert resp.status_code == 200
        data = resp.json()
        # Only in-stock tobacco should appear
        assert len(data) == 1
        assert data[0]["name"] == "Darkside Supernova"
        # Public schema should NOT have is_active, venue_id, etc.
        assert "is_active" not in data[0]
        assert "venue_id" not in data[0]

    @pytest.mark.asyncio
    async def test_public_empty_when_nothing_in_stock(self, client: AsyncClient, venue):
        resp = await client.get("/api/tobaccos/public")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_public_strength_min_filter(
        self, client: AsyncClient, venue, tobacco
    ):
        """strength_min=5 excludes tobacco with strength=4."""
        resp = await client.get("/api/tobaccos/public", params={"strength_min": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert not any(t["id"] == tobacco.id for t in data)

    @pytest.mark.asyncio
    async def test_public_strength_max_filter(
        self, client: AsyncClient, venue, tobacco
    ):
        """strength_max=4 includes tobacco with strength=4."""
        resp = await client.get("/api/tobaccos/public", params={"strength_max": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert any(t["id"] == tobacco.id for t in data)
        assert all(t["strength"] <= 4 for t in data)

    @pytest.mark.asyncio
    async def test_public_strength_range_no_match(
        self, client: AsyncClient, venue, tobacco
    ):
        """strength_min=7 returns empty — only tobacco strength=4 is in stock."""
        resp = await client.get("/api/tobaccos/public", params={"strength_min": 7})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_public_strength_invalid_range(
        self, client: AsyncClient, venue, tobacco
    ):
        """strength_min > strength_max должно вернуть 422."""
        resp = await client.get(
            "/api/tobaccos/public", params={"strength_min": 8, "strength_max": 3}
        )
        assert resp.status_code == 422


class TestTobaccosAdminList:
    @pytest.mark.asyncio
    async def test_list_all(
        self, admin_client: AsyncClient, venue, tobacco, tobacco_out_of_stock
    ):
        resp = await admin_client.get("/api/tobaccos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_filter_strength(
        self, admin_client: AsyncClient, venue, tobacco, tobacco_out_of_stock
    ):
        resp = await admin_client.get("/api/tobaccos?strength=4")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["strength"] == 4 for t in data)
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_list_filter_in_stock(
        self, admin_client: AsyncClient, venue, tobacco, tobacco_out_of_stock
    ):
        resp = await admin_client.get("/api/tobaccos?in_stock=true")
        data = resp.json()
        assert all(t["in_stock"] is True for t in data)

    @pytest.mark.asyncio
    async def test_list_filter_brand(
        self, admin_client: AsyncClient, venue, tobacco, tobacco_out_of_stock
    ):
        resp = await admin_client.get("/api/tobaccos?brand=Tangiers")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["brand"] == "Tangiers"

    @pytest.mark.asyncio
    async def test_list_unauthenticated(self, client: AsyncClient, venue):
        resp = await client.get("/api/tobaccos")
        assert resp.status_code == 401


class TestTobaccosCRUD:
    @pytest.mark.asyncio
    async def test_get_single(self, admin_client: AsyncClient, venue, tobacco):
        resp = await admin_client.get(f"/api/tobaccos/{tobacco.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Darkside Supernova"
        assert data["strength"] == 4

    @pytest.mark.asyncio
    async def test_get_not_found(self, admin_client: AsyncClient, venue):
        resp = await admin_client.get("/api/tobaccos/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create(self, admin_client: AsyncClient, venue):
        resp = await admin_client.post("/api/tobaccos", json={
            "name": "Fumari Blueberry",
            "brand": "Fumari",
            "strength": 2,
            "flavor_profile": ["berry"],
            "in_stock": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Fumari Blueberry"
        assert data["brand"] == "Fumari"
        assert data["strength"] == 2
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_invalid_strength(self, admin_client: AsyncClient, venue):
        resp = await admin_client.post("/api/tobaccos", json={
            "name": "Bad",
            "brand": "Bad",
            "strength": 6,  # Max is 5
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update(self, admin_client: AsyncClient, venue, tobacco):
        resp = await admin_client.put(f"/api/tobaccos/{tobacco.id}", json={
            "in_stock": False,
        })
        assert resp.status_code == 200
        assert resp.json()["in_stock"] is False

    @pytest.mark.asyncio
    async def test_update_empty_body(self, admin_client: AsyncClient, venue, tobacco):
        resp = await admin_client.put(f"/api/tobaccos/{tobacco.id}", json={})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_not_found(self, admin_client: AsyncClient, venue):
        resp = await admin_client.put("/api/tobaccos/9999", json={"name": "X"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete(self, admin_client: AsyncClient, venue, tobacco):
        resp = await admin_client.delete(f"/api/tobaccos/{tobacco.id}")
        assert resp.status_code == 204

        # After soft-delete, should not be found
        get_resp = await admin_client.get(f"/api/tobaccos/{tobacco.id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, admin_client: AsyncClient, venue):
        resp = await admin_client.delete("/api/tobaccos/9999")
        assert resp.status_code == 404
