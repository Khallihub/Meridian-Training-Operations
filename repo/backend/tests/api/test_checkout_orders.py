"""API tests for checkout order endpoints: list, get, cancel."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _seed_session(db):
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session

    loc = Location(name="Ord Site", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Ord Room", capacity=30)
    db.add(room)
    course = Course(title="Ord Course", price=150.0, duration_minutes=90)
    db.add(course)
    await db.flush()
    instr_user = await make_user(db, UserRole.instructor, username="ord_instr")
    instr = Instructor(user_id=instr_user.id)
    db.add(instr)
    await db.flush()
    now = datetime.now(UTC)
    session = Session(
        title="Ord Session",
        course_id=course.id, instructor_id=instr.id, room_id=room.id,
        start_time=now + timedelta(days=2), end_time=now + timedelta(days=2, hours=1),
        capacity=20, created_by=instr_user.id,
    )
    db.add(session)
    await db.flush()
    return session


@pytest.mark.asyncio
class TestOrderEndpoints:
    async def test_list_orders_admin(self, client, db):
        admin = await make_user(db, UserRole.admin, username="ord_admin1")
        token = await get_token(client, "ord_admin1")
        resp = await client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_list_orders_learner(self, client, db):
        session = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="ord_learner1")
        token = await get_token(client, "ord_learner1")

        # Create an order via cart
        await client.post(
            "/api/v1/checkout/cart",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_get_order_by_id(self, client, db):
        session = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="ord_learner2")
        token = await get_token(client, "ord_learner2")

        cart_resp = await client.post(
            "/api/v1/checkout/cart",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        order_id = resp_data(cart_resp)["id"]

        resp = await client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["id"] == order_id

    async def test_cancel_order(self, client, db):
        session = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="ord_learner3")
        token = await get_token(client, "ord_learner3")

        cart_resp = await client.post(
            "/api/v1/checkout/cart",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        order_id = resp_data(cart_resp)["id"]

        resp = await client.patch(f"/api/v1/orders/{order_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["status"] == "canceled"

    async def test_instructor_cannot_access_orders(self, client, db):
        await make_user(db, UserRole.instructor, username="ord_instr2")
        token = await get_token(client, "ord_instr2")
        resp = await client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
