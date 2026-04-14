"""
Authorization tests: role-based 403s and object-level ownership enforcement.

These tests verify that:
- Role guards return 403 for roles that lack access.
- Instructors can only mutate sessions they are assigned to.
- Learners cannot access other learners' bookings or orders.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import make_user, resp_data
from app.modules.users.models import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_session_for_instructor(db, instructor_user_id: uuid.UUID):
    """Create the minimal graph: location → room, course, Instructor → Session."""
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session

    loc = Location(name="Auth Test Site", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Auth Room", capacity=30)
    db.add(room)
    course = Course(title="Auth Course", price=100.0, duration_minutes=60)
    db.add(course)
    await db.flush()
    instructor = Instructor(user_id=instructor_user_id)
    db.add(instructor)
    await db.flush()
    now = datetime.now(UTC)
    session = Session(
        title="Auth Session",
        course_id=course.id,
        instructor_id=instructor.id,
        room_id=room.id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, hours=1),
        capacity=20,
        created_by=instructor_user_id,
    )
    db.add(session)
    await db.flush()
    return session, instructor


async def _get_token(client, username: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPass@1234"},
    )
    return resp_data(resp)["access_token"]


# ---------------------------------------------------------------------------
# Role guard tests (403 for wrong role)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRoleGuards:
    async def test_learner_cannot_create_session(self, client, db):
        learner = await make_user(db, UserRole.learner, username="learner_rg1")
        token = await _get_token(client, "learner_rg1")
        resp = await client.post(
            "/api/v1/sessions",
            json={
                "title": "X", "course_id": str(uuid.uuid4()), "instructor_id": str(uuid.uuid4()),
                "room_id": str(uuid.uuid4()), "start_time": datetime.now(UTC).isoformat(),
                "end_time": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_finance_cannot_create_session(self, client, db):
        await make_user(db, UserRole.finance, username="finance_rg1")
        token = await _get_token(client, "finance_rg1")
        resp = await client.post(
            "/api/v1/sessions",
            json={
                "title": "X", "course_id": str(uuid.uuid4()), "instructor_id": str(uuid.uuid4()),
                "room_id": str(uuid.uuid4()), "start_time": datetime.now(UTC).isoformat(),
                "end_time": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_learner_cannot_cancel_session(self, client, db):
        instr_user = await make_user(db, UserRole.instructor, username="instr_rg2")
        session, _ = await _seed_session_for_instructor(db, instr_user.id)
        learner = await make_user(db, UserRole.learner, username="learner_rg2")
        token = await _get_token(client, "learner_rg2")
        resp = await client.patch(
            f"/api/v1/sessions/{session.id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_list_sessions(self, client, db):
        resp = await client.get("/api/v1/sessions?week=2026-W14")
        assert resp.status_code == 401

    async def test_learner_cannot_go_live(self, client, db):
        instr_user = await make_user(db, UserRole.instructor, username="instr_rg3")
        session, _ = await _seed_session_for_instructor(db, instr_user.id)
        learner = await make_user(db, UserRole.learner, username="learner_rg3")
        token = await _get_token(client, "learner_rg3")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/go-live",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_learner_cannot_view_roster(self, client, db):
        instr_user = await make_user(db, UserRole.instructor, username="instr_rg4")
        session, _ = await _seed_session_for_instructor(db, instr_user.id)
        learner = await make_user(db, UserRole.learner, username="learner_rg4")
        token = await _get_token(client, "learner_rg4")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/roster",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Object-level ownership: instructor can only manage own sessions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestInstructorOwnership:
    async def test_instructor_cannot_cancel_other_instructors_session(self, client, db):
        owner_user = await make_user(db, UserRole.instructor, username="instr_own1")
        other_user = await make_user(db, UserRole.instructor, username="instr_other1")
        session, _ = await _seed_session_for_instructor(db, owner_user.id)

        # other_user gets their own Instructor record (needed so they pass the role check)
        from app.modules.instructors.models import Instructor
        other_instr = Instructor(user_id=other_user.id)
        db.add(other_instr)
        await db.flush()

        token = await _get_token(client, "instr_other1")
        resp = await client.patch(
            f"/api/v1/sessions/{session.id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_instructor_cannot_go_live_other_session(self, client, db):
        owner_user = await make_user(db, UserRole.instructor, username="instr_own2")
        other_user = await make_user(db, UserRole.instructor, username="instr_other2")
        session, _ = await _seed_session_for_instructor(db, owner_user.id)

        from app.modules.instructors.models import Instructor
        other_instr = Instructor(user_id=other_user.id)
        db.add(other_instr)
        await db.flush()

        token = await _get_token(client, "instr_other2")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/go-live",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_instructor_cannot_view_roster_of_other_session(self, client, db):
        owner_user = await make_user(db, UserRole.instructor, username="instr_own3")
        other_user = await make_user(db, UserRole.instructor, username="instr_other3")
        session, _ = await _seed_session_for_instructor(db, owner_user.id)

        from app.modules.instructors.models import Instructor
        other_instr = Instructor(user_id=other_user.id)
        db.add(other_instr)
        await db.flush()

        token = await _get_token(client, "instr_other3")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/roster",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_assigned_instructor_can_go_live_own_session(self, client, db):
        owner_user = await make_user(db, UserRole.instructor, username="instr_own4")
        session, _ = await _seed_session_for_instructor(db, owner_user.id)
        token = await _get_token(client, "instr_own4")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/go-live",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Expect success (200) — session was in scheduled state
        assert resp.status_code == 200
        assert resp_data(resp)["status"] == "live"


# ---------------------------------------------------------------------------
# Cross-learner isolation: learner cannot see another learner's data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCrossLearnerIsolation:
    async def test_learner_cannot_view_other_learners_booking(self, client, db):
        from app.modules.bookings.models import Booking, BookingStatus
        from app.modules.locations.models import Location, Room
        from app.modules.courses.models import Course
        from app.modules.instructors.models import Instructor
        from app.modules.sessions.models import Session

        # Seed a session
        loc = Location(name="Isolation Site", timezone="UTC")
        db.add(loc)
        await db.flush()
        room = Room(location_id=loc.id, name="Room I", capacity=10)
        db.add(room)
        course = Course(title="Iso Course", price=50.0, duration_minutes=60)
        db.add(course)
        await db.flush()
        instr_u = await make_user(db, UserRole.instructor, username="instr_iso")
        instr = Instructor(user_id=instr_u.id)
        db.add(instr)
        await db.flush()
        now = datetime.now(UTC)
        session = Session(
            title="Iso Session", course_id=course.id, instructor_id=instr.id,
            room_id=room.id, start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=3, hours=1), capacity=10, created_by=instr_u.id,
        )
        db.add(session)
        await db.flush()

        # learner_a creates a booking
        learner_a = await make_user(db, UserRole.learner, username="learner_iso_a")
        booking = Booking(
            session_id=session.id, learner_id=learner_a.id,
            status=BookingStatus.confirmed,
        )
        db.add(booking)
        await db.flush()

        # learner_b tries to fetch learner_a's booking by ID
        learner_b = await make_user(db, UserRole.learner, username="learner_iso_b")
        token_b = await _get_token(client, "learner_iso_b")
        resp = await client.get(
            f"/api/v1/bookings/{booking.id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        # Must be 403 or 404 — learner_b should not see learner_a's booking
        assert resp.status_code in (403, 404)

    async def test_learner_cannot_view_other_learners_order(self, client, db):
        from app.modules.checkout.models import Order, OrderStatus

        learner_a = await make_user(db, UserRole.learner, username="learner_order_a")
        learner_b = await make_user(db, UserRole.learner, username="learner_order_b")

        order = Order(
            learner_id=learner_a.id,
            status=OrderStatus.paid,
            subtotal=100.0,
            total=100.0,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(order)
        await db.flush()

        token_b = await _get_token(client, "learner_order_b")
        resp = await client.get(
            f"/api/v1/checkout/orders/{order.id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code in (403, 404)
