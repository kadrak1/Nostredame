"""Integration tests for /api/bookings and /api/admin/bookings endpoints."""

import pytest
from httpx import AsyncClient


PHONE = "+79991234567"
BOOKING_DATE = "2026-06-15"


class TestAvailableTables:
    @pytest.mark.asyncio
    async def test_available_tables(self, client: AsyncClient, venue, table, table2):
        resp = await client.get("/api/bookings/available-tables", params={
            "date": "2026-07-01",
            "time_from": "18:00",
            "time_to": "21:00",
            "guests": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        numbers = {t["number"] for t in data}
        assert numbers == {1, 2}

    @pytest.mark.asyncio
    async def test_available_tables_filters_by_capacity(
        self, client: AsyncClient, venue, table, table2
    ):
        """table has capacity=4, table2 has capacity=6. Asking for 5 → only table2."""
        resp = await client.get("/api/bookings/available-tables", params={
            "date": "2026-07-01",
            "time_from": "18:00",
            "time_to": "21:00",
            "guests": 5,
        })
        data = resp.json()
        assert len(data) == 1
        assert data[0]["number"] == 2

    @pytest.mark.asyncio
    async def test_available_tables_excludes_booked(
        self, client: AsyncClient, venue, table, table2, booking
    ):
        """booking occupies table on 2026-06-15 19:00-22:00 → table unavailable."""
        resp = await client.get("/api/bookings/available-tables", params={
            "date": BOOKING_DATE,
            "time_from": "20:00",
            "time_to": "23:00",
            "guests": 1,
        })
        data = resp.json()
        # Only table2 should be available (table is booked)
        ids = {t["id"] for t in data}
        assert table.id not in ids
        assert table2.id in ids

    @pytest.mark.asyncio
    async def test_available_tables_invalid_time_order(
        self, client: AsyncClient, venue, table
    ):
        resp = await client.get("/api/bookings/available-tables", params={
            "date": "2026-07-01",
            "time_from": "21:00",
            "time_to": "18:00",
            "guests": 1,
        })
        assert resp.status_code == 422


class TestCreateBooking:
    @pytest.mark.asyncio
    async def test_create_booking_success(
        self, client: AsyncClient, venue, table
    ):
        resp = await client.post("/api/bookings", json={
            "table_id": table.id,
            "date": "2026-08-01",
            "time_from": "18:00:00",
            "time_to": "21:00:00",
            "guest_count": 3,
            "guest_name": "Александр",
            "guest_phone": "+79990001122",
            "notes": "День рождения",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["table_id"] == table.id
        assert data["guest_count"] == 3
        assert data["guest_name"] == "Александр"
        assert data["status"] == "pending"
        assert data["notes"] == "День рождения"

    @pytest.mark.asyncio
    async def test_create_booking_conflict(
        self, client: AsyncClient, venue, table, booking
    ):
        """Booking exists for table on 2026-06-15 19:00-22:00 → overlap → 409."""
        resp = await client.post("/api/bookings", json={
            "table_id": table.id,
            "date": BOOKING_DATE,
            "time_from": "20:00:00",
            "time_to": "23:00:00",
            "guest_count": 2,
            "guest_name": "Overlap",
            "guest_phone": "+79998887766",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_booking_table_not_found(
        self, client: AsyncClient, venue
    ):
        resp = await client.post("/api/bookings", json={
            "table_id": 9999,
            "date": "2026-08-01",
            "time_from": "18:00:00",
            "time_to": "21:00:00",
            "guest_count": 2,
            "guest_name": "Ghost",
            "guest_phone": "+79990001122",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_booking_exceeds_capacity(
        self, client: AsyncClient, venue, table
    ):
        """table has capacity=4, requesting 5 guests → 409."""
        resp = await client.post("/api/bookings", json={
            "table_id": table.id,
            "date": "2026-08-01",
            "time_from": "18:00:00",
            "time_to": "21:00:00",
            "guest_count": 5,
            "guest_name": "BigGroup",
            "guest_phone": "+79990001122",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_booking_invalid_phone(
        self, client: AsyncClient, venue, table
    ):
        resp = await client.post("/api/bookings", json={
            "table_id": table.id,
            "date": "2026-08-01",
            "time_from": "18:00:00",
            "time_to": "21:00:00",
            "guest_count": 2,
            "guest_name": "BadPhone",
            "guest_phone": "123",  # Too short
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_booking_time_order_invalid(
        self, client: AsyncClient, venue, table
    ):
        resp = await client.post("/api/bookings", json={
            "table_id": table.id,
            "date": "2026-08-01",
            "time_from": "21:00:00",
            "time_to": "18:00:00",
            "guest_count": 2,
            "guest_name": "Reversed",
            "guest_phone": "+79990001122",
        })
        assert resp.status_code == 422


class TestGetBooking:
    @pytest.mark.asyncio
    async def test_get_booking_by_id(self, client: AsyncClient, venue, table, booking):
        resp = await client.get(f"/api/bookings/{booking.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == booking.id
        assert data["status"] == "pending"
        # Public schema should NOT contain phone
        assert "guest_phone_encrypted" not in data
        assert "guest_phone_masked" not in data

    @pytest.mark.asyncio
    async def test_get_booking_not_found(self, client: AsyncClient, venue):
        resp = await client.get("/api/bookings/9999")
        assert resp.status_code == 404


class TestCancelBooking:
    @pytest.mark.asyncio
    async def test_cancel_with_correct_phone(
        self, client: AsyncClient, venue, table, booking
    ):
        resp = await client.put(f"/api/bookings/{booking.id}/cancel", json={
            "guest_phone": PHONE,
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_with_wrong_phone(
        self, client: AsyncClient, venue, table, booking
    ):
        resp = await client.put(f"/api/bookings/{booking.id}/cancel", json={
            "guest_phone": "+70000000000",
        })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, client: AsyncClient, venue):
        resp = await client.put("/api/bookings/9999/cancel", json={
            "guest_phone": PHONE,
        })
        assert resp.status_code == 404


class TestBookingOrders:
    """Tests for POST/GET /api/bookings/{id}/orders."""

    @pytest.mark.asyncio
    async def test_create_order_success(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        resp = await client.post(
            f"/api/bookings/{booking.id}/orders",
            json={
                "guest_phone": PHONE,
                "strength": 5,
                "notes": "Тест заказа",
                "items": [{"tobacco_id": tobacco.id, "weight_grams": 20}],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["booking_id"] == booking.id
        assert data["strength"] == 5
        assert data["source"] == "booking_preorder"
        assert data["notes"] == "Тест заказа"
        assert len(data["items"]) == 1
        assert data["items"][0]["tobacco_name"] == tobacco.name
        assert data["items"][0]["weight_grams"] == 20

    @pytest.mark.asyncio
    async def test_create_order_wrong_phone(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        resp = await client.post(
            f"/api/bookings/{booking.id}/orders",
            json={
                "guest_phone": "+70000000000",
                "strength": 5,
                "items": [{"tobacco_id": tobacco.id}],
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_order_booking_not_found(
        self, client: AsyncClient, venue, tobacco
    ):
        resp = await client.post(
            "/api/bookings/9999/orders",
            json={
                "guest_phone": PHONE,
                "strength": 5,
                "items": [{"tobacco_id": tobacco.id}],
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_order_tobacco_not_found(
        self, client: AsyncClient, venue, table, booking
    ):
        resp = await client.post(
            f"/api/bookings/{booking.id}/orders",
            json={
                "guest_phone": PHONE,
                "strength": 5,
                "items": [{"tobacco_id": 9999}],
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_order_tobacco_out_of_stock(
        self, client: AsyncClient, venue, table, booking, tobacco_out_of_stock
    ):
        resp = await client.post(
            f"/api/bookings/{booking.id}/orders",
            json={
                "guest_phone": PHONE,
                "strength": 5,
                "items": [{"tobacco_id": tobacco_out_of_stock.id}],
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_order_invalid_strength(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        for bad_strength in (0, 11):
            resp = await client.post(
                f"/api/bookings/{booking.id}/orders",
                json={
                    "guest_phone": PHONE,
                    "strength": bad_strength,
                    "items": [{"tobacco_id": tobacco.id}],
                },
            )
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_order_boundary_strength(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        """Граничные значения 1 и 10 должны быть допустимы."""
        for strength in (1, 10):
            resp = await client.post(
                f"/api/bookings/{booking.id}/orders",
                json={
                    "guest_phone": PHONE,
                    "strength": strength,
                    "items": [{"tobacco_id": tobacco.id}],
                },
            )
            assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_order_duplicate_tobaccos(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        """Дублирующиеся tobacco_id в items должны вернуть 422."""
        resp = await client.post(
            f"/api/bookings/{booking.id}/orders",
            json={
                "guest_phone": PHONE,
                "strength": 5,
                "items": [
                    {"tobacco_id": tobacco.id},
                    {"tobacco_id": tobacco.id},
                ],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_order_cancelled_booking(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        """Нельзя создать заказ к отменённой брони."""
        # Сначала отменяем бронь
        await client.put(f"/api/bookings/{booking.id}/cancel", json={"guest_phone": PHONE})
        resp = await client.post(
            f"/api/bookings/{booking.id}/orders",
            json={
                "guest_phone": PHONE,
                "strength": 5,
                "items": [{"tobacco_id": tobacco.id}],
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_order_exceeds_max(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        """6-й заказ к одной брони должен вернуть 400."""
        payload = {
            "guest_phone": PHONE,
            "strength": 3,
            "items": [{"tobacco_id": tobacco.id}],
        }
        for _ in range(5):
            r = await client.post(f"/api/bookings/{booking.id}/orders", json=payload)
            assert r.status_code == 201
        resp = await client.post(f"/api/bookings/{booking.id}/orders", json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_orders_success(
        self, client: AsyncClient, venue, table, booking, tobacco
    ):
        await client.post(
            f"/api/bookings/{booking.id}/orders",
            json={
                "guest_phone": PHONE,
                "strength": 5,
                "items": [{"tobacco_id": tobacco.id}],
            },
        )
        resp = await client.get(
            f"/api/bookings/{booking.id}/orders",
            params={"guest_phone": PHONE},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["booking_id"] == booking.id
        assert data[0]["items"][0]["tobacco_name"] == tobacco.name

    @pytest.mark.asyncio
    async def test_list_orders_wrong_phone(
        self, client: AsyncClient, venue, table, booking
    ):
        resp = await client.get(
            f"/api/bookings/{booking.id}/orders",
            params={"guest_phone": "+70000000000"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_orders_booking_not_found(self, client: AsyncClient, venue):
        resp = await client.get(
            "/api/bookings/9999/orders",
            params={"guest_phone": PHONE},
        )
        assert resp.status_code == 404


class TestAdminBookings:
    @pytest.mark.asyncio
    async def test_list_admin_bookings(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        resp = await admin_client.get("/api/admin/bookings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        # Admin schema should have masked phone
        assert "guest_phone_masked" in data[0]
        assert "***" in data[0]["guest_phone_masked"]

    @pytest.mark.asyncio
    async def test_list_admin_bookings_filter_date(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        resp = await admin_client.get("/api/admin/bookings", params={
            "date": BOOKING_DATE,
        })
        data = resp.json()
        assert len(data) >= 1
        assert all(b["date"] == BOOKING_DATE for b in data)

    @pytest.mark.asyncio
    async def test_list_admin_bookings_filter_status(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        resp = await admin_client.get("/api/admin/bookings", params={
            "status": "pending",
        })
        data = resp.json()
        assert all(b["status"] == "pending" for b in data)

    @pytest.mark.asyncio
    async def test_list_admin_bookings_unauthenticated(
        self, client: AsyncClient, venue
    ):
        resp = await client.get("/api/admin/bookings")
        assert resp.status_code == 401


class TestAdminBookingActions:
    @pytest.mark.asyncio
    async def test_confirm_pending_booking(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        resp = await admin_client.put(f"/api/admin/bookings/{booking.id}/confirm")
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_confirm_non_pending_fails(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        # Confirm first
        await admin_client.put(f"/api/admin/bookings/{booking.id}/confirm")
        # Confirm again → 409
        resp = await admin_client.put(f"/api/admin/bookings/{booking.id}/confirm")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_reject_booking(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        resp = await admin_client.put(f"/api/admin/bookings/{booking.id}/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_reject_already_cancelled_fails(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        await admin_client.put(f"/api/admin/bookings/{booking.id}/reject")
        resp = await admin_client.put(f"/api/admin/bookings/{booking.id}/reject")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_complete_confirmed_booking(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        # Must be confirmed first
        await admin_client.put(f"/api/admin/bookings/{booking.id}/confirm")
        resp = await admin_client.put(f"/api/admin/bookings/{booking.id}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_complete_pending_fails(
        self, admin_client: AsyncClient, venue, table, booking
    ):
        """Cannot complete a pending booking — must confirm first."""
        resp = await admin_client.put(f"/api/admin/bookings/{booking.id}/complete")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_admin_action_not_found(
        self, admin_client: AsyncClient, venue
    ):
        resp = await admin_client.put("/api/admin/bookings/9999/confirm")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_actions_unauthenticated(
        self, client: AsyncClient, venue, table, booking
    ):
        resp = await client.put(f"/api/admin/bookings/{booking.id}/confirm")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_hookah_master_cannot_manage_bookings(
        self, master_client: AsyncClient, venue, table, booking
    ):
        """hookah_master role should not manage bookings."""
        resp = await master_client.put(f"/api/admin/bookings/{booking.id}/confirm")
        assert resp.status_code == 403
