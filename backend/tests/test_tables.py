"""Integration tests for /api/tables and /api/venue/floor-plan endpoints."""

import pytest
from httpx import AsyncClient


class TestFloorPlan:
    @pytest.mark.asyncio
    async def test_get_floor_plan_public(self, client: AsyncClient, venue, table):
        resp = await client.get("/api/venue/floor-plan")
        assert resp.status_code == 200
        data = resp.json()
        assert "floor_plan" in data
        assert "tables" in data
        assert len(data["tables"]) >= 1
        assert data["tables"][0]["number"] == 1

    @pytest.mark.asyncio
    async def test_get_floor_plan_no_venue_404(self, client: AsyncClient):
        resp = await client.get("/api/venue/floor-plan")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_put_floor_plan_as_admin(self, admin_client: AsyncClient, venue):
        plan = {"width": 1200, "height": 800, "walls": []}
        resp = await admin_client.put("/api/venue/floor-plan", json={"floor_plan": plan})
        assert resp.status_code == 200
        assert resp.json()["floor_plan"]["width"] == 1200

    @pytest.mark.asyncio
    async def test_put_floor_plan_unauthenticated(self, client: AsyncClient, venue):
        resp = await client.put("/api/venue/floor-plan", json={"floor_plan": {}})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_put_floor_plan_hookah_master_forbidden(self, master_client: AsyncClient, venue):
        resp = await master_client.put("/api/venue/floor-plan", json={"floor_plan": {}})
        assert resp.status_code == 403


class TestTablesListCreate:
    @pytest.mark.asyncio
    async def test_list_tables(self, admin_client: AsyncClient, venue, table, table2):
        resp = await admin_client.get("/api/tables")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        numbers = [t["number"] for t in data]
        assert 1 in numbers
        assert 2 in numbers

    @pytest.mark.asyncio
    async def test_list_tables_unauthenticated(self, client: AsyncClient, venue):
        resp = await client.get("/api/tables")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_table(self, admin_client: AsyncClient, venue):
        resp = await admin_client.post("/api/tables", json={
            "number": 10,
            "capacity": 8,
            "x": 200,
            "y": 200,
            "width": 100,
            "height": 100,
            "shape": "circle",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["number"] == 10
        assert data["capacity"] == 8
        assert data["shape"] == "circle"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_table_duplicate_number(self, admin_client: AsyncClient, venue, table):
        """Table #1 already exists → 409."""
        resp = await admin_client.post("/api/tables", json={
            "number": 1,
            "capacity": 2,
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_table_invalid_capacity(self, admin_client: AsyncClient, venue):
        resp = await admin_client.post("/api/tables", json={
            "number": 99,
            "capacity": 0,  # Must be >= 1
        })
        assert resp.status_code == 422


class TestTablesUpdateDelete:
    @pytest.mark.asyncio
    async def test_update_table(self, admin_client: AsyncClient, venue, table):
        resp = await admin_client.put(f"/api/tables/{table.id}", json={
            "capacity": 6,
        })
        assert resp.status_code == 200
        assert resp.json()["capacity"] == 6

    @pytest.mark.asyncio
    async def test_update_table_empty_body(self, admin_client: AsyncClient, venue, table):
        resp = await admin_client.put(f"/api/tables/{table.id}", json={})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_table_not_found(self, admin_client: AsyncClient, venue):
        resp = await admin_client.put("/api/tables/9999", json={"capacity": 2})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_table(self, admin_client: AsyncClient, venue, table):
        resp = await admin_client.delete(f"/api/tables/{table.id}")
        assert resp.status_code == 204

        # After soft-delete, table should not appear in list
        list_resp = await admin_client.get("/api/tables")
        assert resp.status_code == 204
        ids = [t["id"] for t in list_resp.json()]
        assert table.id not in ids

    @pytest.mark.asyncio
    async def test_delete_table_not_found(self, admin_client: AsyncClient, venue):
        resp = await admin_client.delete("/api/tables/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_with_include_inactive(self, admin_client: AsyncClient, venue, table):
        # Delete the table (soft)
        await admin_client.delete(f"/api/tables/{table.id}")

        # Without flag — empty
        resp = await admin_client.get("/api/tables")
        assert len(resp.json()) == 0

        # With flag — shows it
        resp = await admin_client.get("/api/tables?include_inactive=true")
        assert len(resp.json()) == 1
        assert resp.json()[0]["is_active"] is False


class TestQRCodes:
    @pytest.mark.asyncio
    async def test_get_single_qr(self, admin_client: AsyncClient, venue, table):
        """GET /tables/{id}/qr returns PNG bytes."""
        resp = await admin_client.get(f"/api/tables/{table.id}/qr")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        # PNG magic bytes: \x89PNG
        assert resp.content[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_get_single_qr_custom_size(self, admin_client: AsyncClient, venue, table):
        resp = await admin_client.get(f"/api/tables/{table.id}/qr?size=600")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    @pytest.mark.asyncio
    async def test_get_single_qr_invalid_size(self, admin_client: AsyncClient, venue, table):
        """size < 100 or > 2000 → 422."""
        resp = await admin_client.get(f"/api/tables/{table.id}/qr?size=50")
        assert resp.status_code == 422
        resp = await admin_client.get(f"/api/tables/{table.id}/qr?size=9999")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_single_qr_not_found(self, admin_client: AsyncClient, venue):
        resp = await admin_client.get("/api/tables/9999/qr")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_single_qr_unauthenticated(self, client: AsyncClient, venue, table):
        resp = await client.get(f"/api/tables/{table.id}/qr")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_all_qr_zip(self, admin_client: AsyncClient, venue, table, table2):
        """GET /tables/qr-all returns a valid ZIP containing PNGs."""
        import zipfile
        import io

        resp = await admin_client.get("/api/tables/qr-all")
        assert resp.status_code == 200
        assert "zip" in resp.headers["content-type"]

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert "table_1.png" in names
        assert "table_2.png" in names
        # Each file is a valid PNG
        for name in names:
            assert zf.read(name)[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_get_all_qr_unauthenticated(self, client: AsyncClient, venue):
        resp = await client.get("/api/tables/qr-all")
        assert resp.status_code == 401
