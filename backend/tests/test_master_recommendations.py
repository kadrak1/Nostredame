"""Integration tests for /api/master/recommendations endpoints."""

import pytest
from httpx import AsyncClient


class TestPublicGet:
    @pytest.mark.asyncio
    async def test_list_public_no_filter(
        self, client: AsyncClient, venue, master_recommendation
    ):
        resp = await client.get("/api/master/recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        rec = next(r for r in data if r["id"] == master_recommendation.id)
        assert rec["name"] == master_recommendation.name
        assert rec["strength_level"] == master_recommendation.strength_level

    @pytest.mark.asyncio
    async def test_list_public_filter_strength(
        self, client: AsyncClient, venue, master_recommendation
    ):
        """Filter by strength_level returns only matching."""
        resp = await client.get(
            "/api/master/recommendations", params={"strength_level": "light"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["strength_level"] == "light" for r in data)

    @pytest.mark.asyncio
    async def test_list_public_filter_no_match(
        self, client: AsyncClient, venue, master_recommendation
    ):
        """Filter for 'strong' returns empty when only 'light' exists."""
        resp = await client.get(
            "/api/master/recommendations", params={"strength_level": "strong"}
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_public_hides_inactive(
        self, client: AsyncClient, master_client: AsyncClient, venue, master_recommendation
    ):
        """Soft-deleted recommendations are hidden from public."""
        await master_client.delete(f"/api/master/recommendations/{master_recommendation.id}")
        resp = await client.get("/api/master/recommendations")
        ids = [r["id"] for r in resp.json()]
        assert master_recommendation.id not in ids


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_success(
        self, master_client: AsyncClient, venue, tobacco
    ):
        resp = await master_client.post(
            "/api/master/recommendations",
            json={
                "name": "Фруктовый микс",
                "strength_level": "medium",
                "items": [{"tobacco_id": tobacco.id, "weight_grams": 20}],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Фруктовый микс"
        assert data["strength_level"] == "medium"
        assert len(data["items"]) == 1
        assert data["items"][0]["tobacco_id"] == tobacco.id

    @pytest.mark.asyncio
    async def test_create_unauthenticated(self, client: AsyncClient, venue, tobacco):
        resp = await client.post(
            "/api/master/recommendations",
            json={
                "name": "Test",
                "strength_level": "light",
                "items": [{"tobacco_id": tobacco.id}],
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_invalid_strength_level(
        self, master_client: AsyncClient, venue, tobacco
    ):
        resp = await master_client.post(
            "/api/master/recommendations",
            json={
                "name": "Bad",
                "strength_level": "extreme",  # invalid
                "items": [{"tobacco_id": tobacco.id}],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_invalid_tobacco_id(
        self, master_client: AsyncClient, venue
    ):
        """Несуществующий tobacco_id должен вернуть 400."""
        resp = await master_client.post(
            "/api/master/recommendations",
            json={
                "name": "Плохой",
                "strength_level": "light",
                "items": [{"tobacco_id": 9999}],
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_duplicate_tobaccos(
        self, master_client: AsyncClient, venue, tobacco
    ):
        resp = await master_client.post(
            "/api/master/recommendations",
            json={
                "name": "Дубль",
                "strength_level": "light",
                "items": [
                    {"tobacco_id": tobacco.id},
                    {"tobacco_id": tobacco.id},
                ],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_exceeds_max(
        self, master_client: AsyncClient, venue, tobacco
    ):
        """11-я активная рекомендация должна вернуть 400."""
        for i in range(10):
            r = await master_client.post(
                "/api/master/recommendations",
                json={
                    "name": f"Рек {i}",
                    "strength_level": "light",
                    "items": [{"tobacco_id": tobacco.id}],
                },
            )
            assert r.status_code == 201
        resp = await master_client.post(
            "/api/master/recommendations",
            json={
                "name": "Лишняя",
                "strength_level": "light",
                "items": [{"tobacco_id": tobacco.id}],
            },
        )
        assert resp.status_code == 400


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_name(
        self, master_client: AsyncClient, venue, master_recommendation
    ):
        resp = await master_client.put(
            f"/api/master/recommendations/{master_recommendation.id}",
            json={"name": "Новое название"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Новое название"

    @pytest.mark.asyncio
    async def test_update_empty_body(
        self, master_client: AsyncClient, venue, master_recommendation
    ):
        resp = await master_client.put(
            f"/api/master/recommendations/{master_recommendation.id}", json={}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_not_found(self, master_client: AsyncClient, venue):
        resp = await master_client.put(
            "/api/master/recommendations/9999", json={"name": "X"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_items(
        self, master_client: AsyncClient, venue, tobacco, master_recommendation
    ):
        """Обновление items с валидным tobacco_id."""
        resp = await master_client.put(
            f"/api/master/recommendations/{master_recommendation.id}",
            json={"items": [{"tobacco_id": tobacco.id, "weight_grams": 30}]},
        )
        assert resp.status_code == 200
        assert resp.json()["items"][0]["weight_grams"] == 30

    @pytest.mark.asyncio
    async def test_update_items_invalid_tobacco(
        self, master_client: AsyncClient, venue, master_recommendation
    ):
        """Несуществующий tobacco_id должен вернуть 400."""
        resp = await master_client.put(
            f"/api/master/recommendations/{master_recommendation.id}",
            json={"items": [{"tobacco_id": 9999}]},
        )
        assert resp.status_code == 400


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_success(
        self, master_client: AsyncClient, venue, master_recommendation
    ):
        resp = await master_client.delete(
            f"/api/master/recommendations/{master_recommendation.id}"
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(self, master_client: AsyncClient, venue):
        resp = await master_client.delete("/api/master/recommendations/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthenticated(
        self, client: AsyncClient, venue, master_recommendation
    ):
        resp = await client.delete(
            f"/api/master/recommendations/{master_recommendation.id}"
        )
        assert resp.status_code == 401
