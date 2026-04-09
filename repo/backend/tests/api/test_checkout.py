"""API tests for checkout and best-offer engine."""

import pytest
from datetime import UTC, datetime, timedelta

from tests.conftest import make_user
from app.modules.users.models import UserRole


async def _seed_session(db):
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session
    from app.modules.users.models import User

    loc = Location(name="Site X", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Room B", capacity=30)
    db.add(room)
    course = Course(title="Advanced Python", price=150.0, duration_minutes=90)
    db.add(course)
    await db.flush()
    instr_user = await make_user(db, UserRole.instructor, username="instr_co")
    instr = Instructor(user_id=instr_user.id)
    db.add(instr)
    await db.flush()
    now = datetime.now(UTC)
    session = Session(
        course_id=course.id, instructor_id=instr.id, room_id=room.id,
        start_time=now + timedelta(days=2), end_time=now + timedelta(days=2, hours=1),
        capacity=20, created_by=instr_user.id,
    )
    db.add(session)
    await db.flush()
    return session, course


@pytest.mark.asyncio
class TestCheckout:
    async def test_create_cart_auto_best_offer(self, client, db):
        session, course = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="learner_co")
        token = (await client.post("/api/auth/login", json={"username": "learner_co", "password": "TestPass@1234"})).json()["access_token"]

        # Add a promotion
        from app.modules.promotions.models import Promotion, PromotionType
        from datetime import UTC, datetime, timedelta
        promo = Promotion(
            name="10% off",
            type=PromotionType.pct_off,
            value=10.0,
            applies_to={"all": True},
            is_active=True,
            valid_from=datetime.now(UTC) - timedelta(hours=1),
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(promo)
        await db.flush()

        resp = await client.post(
            "/api/checkout/cart",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["subtotal"] == 150.0
        assert data["discount_total"] == pytest.approx(15.0)
        assert data["total"] == pytest.approx(135.0)
        assert len(data["applied_promotions"]) == 1

    async def test_best_offer_dry_run(self, client, db):
        session, _ = await _seed_session(db)
        admin = await make_user(db, UserRole.admin, username="admin_bo")
        token = (await client.post("/api/auth/login", json={"username": "admin_bo", "password": "TestPass@1234"})).json()["access_token"]

        resp = await client.post(
            "/api/checkout/best-offer",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "subtotal" in data
        assert "applied_promotions" in data
