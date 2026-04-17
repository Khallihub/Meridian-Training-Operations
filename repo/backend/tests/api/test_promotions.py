"""API tests for promotions CRUD and preview endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="prm_admin")
    return await get_token(client, "prm_admin")


async def _finance_token(client, db):
    await make_user(db, UserRole.finance, username="prm_finance")
    return await get_token(client, "prm_finance")


def _promo_payload(name="Test Promo"):
    now = datetime.now(UTC)
    return {
        "name": name,
        "type": "percent_off",
        "value": 15.0,
        "applies_to": {"all": True},
        "valid_from": (now - timedelta(hours=1)).isoformat(),
        "valid_until": (now + timedelta(days=30)).isoformat(),
    }


@pytest.mark.asyncio
class TestPromotionsCRUD:
    async def test_create_promotion(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.post(
            "/api/v1/promotions",
            json=_promo_payload("Create Promo"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert data["name"] == "Create Promo"
        assert data["type"] == "percent_off"
        assert data["value"] == 15.0

    async def test_finance_can_create_promotion(self, client, db):
        token = await _finance_token(client, db)
        resp = await client.post(
            "/api/v1/promotions",
            json=_promo_payload("Finance Promo"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    async def test_list_promotions(self, client, db):
        token = await _admin_token(client, db)
        await client.post(
            "/api/v1/promotions",
            json=_promo_payload("List Promo"),
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get("/api/v1/promotions", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)

    async def test_get_promotion(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/promotions",
            json=_promo_payload("Get Promo"),
            headers={"Authorization": f"Bearer {token}"},
        )
        promo_id = resp_data(create_resp)["id"]
        resp = await client.get(f"/api/v1/promotions/{promo_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp_data(resp)["name"] == "Get Promo"

    async def test_update_promotion(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/promotions",
            json=_promo_payload("Old Promo"),
            headers={"Authorization": f"Bearer {token}"},
        )
        promo_id = resp_data(create_resp)["id"]
        resp = await client.patch(
            f"/api/v1/promotions/{promo_id}",
            json={"name": "Updated Promo", "value": 20.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["name"] == "Updated Promo"
        assert data["value"] == 20.0

    async def test_delete_promotion(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/promotions",
            json=_promo_payload("Del Promo"),
            headers={"Authorization": f"Bearer {token}"},
        )
        promo_id = resp_data(create_resp)["id"]
        resp = await client.delete(f"/api/v1/promotions/{promo_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

    async def test_get_nonexistent_promotion_returns_404(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get(f"/api/v1/promotions/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestPromotionPreview:
    async def test_preview_promotions(self, client, db):
        token = await _admin_token(client, db)
        # Create a session for the cart
        from app.modules.locations.models import Location, Room
        from app.modules.courses.models import Course
        from app.modules.instructors.models import Instructor
        from app.modules.sessions.models import Session

        loc = Location(name="Promo Site", timezone="UTC")
        db.add(loc)
        await db.flush()
        room = Room(location_id=loc.id, name="Promo Room", capacity=30)
        db.add(room)
        course = Course(title="Promo Course", price=200.0)
        db.add(course)
        await db.flush()
        instr_user = await make_user(db, UserRole.instructor, username="prm_instr")
        instr = Instructor(user_id=instr_user.id)
        db.add(instr)
        await db.flush()
        now = datetime.now(UTC)
        session = Session(
            title="Promo Session",
            course_id=course.id, instructor_id=instr.id, room_id=room.id,
            start_time=now + timedelta(days=2), end_time=now + timedelta(days=2, hours=1),
            capacity=20, created_by=instr_user.id,
        )
        db.add(session)
        await db.flush()

        resp = await client.post(
            "/api/v1/promotions/preview",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "subtotal" in data
        assert "applied_promotions" in data

    async def test_learner_cannot_preview(self, client, db):
        await make_user(db, UserRole.learner, username="prm_learner")
        token = await get_token(client, "prm_learner")
        resp = await client.post(
            "/api/v1/promotions/preview",
            json={"items": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
