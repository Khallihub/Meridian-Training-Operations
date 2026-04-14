"""API tests for attendance authorization matrix."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import make_user, resp_data
from app.modules.users.models import UserRole


async def _seed_live_session(db, instructor_user_id: uuid.UUID):
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session, SessionStatus

    loc = Location(name="Att Site", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Att Room", capacity=20)
    db.add(room)
    course = Course(title="Att Course", price=50.0, duration_minutes=60)
    db.add(course)
    await db.flush()
    instructor = Instructor(user_id=instructor_user_id)
    db.add(instructor)
    await db.flush()
    now = datetime.now(UTC)
    session = Session(
        title="Att Session",
        course_id=course.id,
        instructor_id=instructor.id,
        room_id=room.id,
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(hours=1),
        capacity=10,
        status=SessionStatus.live,
        created_by=instructor_user_id,
    )
    db.add(session)
    await db.flush()
    return session, instructor


async def _confirmed_booking(db, session_id: uuid.UUID, learner_id: uuid.UUID):
    from app.modules.bookings.models import Booking, BookingStatus
    booking = Booking(session_id=session_id, learner_id=learner_id, status=BookingStatus.confirmed)
    db.add(booking)
    await db.flush()
    return booking


async def _token(client, username: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": "TestPass@1234"})
    return resp_data(resp)["access_token"]


@pytest.mark.asyncio
class TestAttendanceAuthMatrix:
    async def test_learner_cannot_checkin_others(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr1")
        session, _ = await _seed_live_session(db, owner.id)
        learner_a = await make_user(db, UserRole.learner, username="att_learn1a")
        learner_b = await make_user(db, UserRole.learner, username="att_learn1b")
        await _confirmed_booking(db, session.id, learner_a.id)
        token = await _token(client, "att_learn1b")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/attendance/checkin",
            json={"learner_id": str(learner_a.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unassigned_instructor_cannot_checkin(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr2")
        session, _ = await _seed_live_session(db, owner.id)
        other = await make_user(db, UserRole.instructor, username="att_instr2b")
        learner = await make_user(db, UserRole.learner, username="att_learn2")
        await _confirmed_booking(db, session.id, learner.id)
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()
        token = await _token(client, "att_instr2b")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/attendance/checkin",
            json={"learner_id": str(learner.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_assigned_instructor_can_checkin(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr3")
        session, _ = await _seed_live_session(db, owner.id)
        learner = await make_user(db, UserRole.learner, username="att_learn3")
        await _confirmed_booking(db, session.id, learner.id)
        token = await _token(client, "att_instr3")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/attendance/checkin",
            json={"learner_id": str(learner.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_unassigned_instructor_cannot_checkout(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr4")
        session, _ = await _seed_live_session(db, owner.id)
        other = await make_user(db, UserRole.instructor, username="att_instr4b")
        learner = await make_user(db, UserRole.learner, username="att_learn4")
        await _confirmed_booking(db, session.id, learner.id)
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()
        token = await _token(client, "att_instr4b")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/attendance/checkout",
            json={"learner_id": str(learner.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_learner_cannot_view_stats(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr5")
        session, _ = await _seed_live_session(db, owner.id)
        learner = await make_user(db, UserRole.learner, username="att_learn5")
        token = await _token(client, "att_learn5")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/attendance/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unassigned_instructor_cannot_view_stats(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr6")
        session, _ = await _seed_live_session(db, owner.id)
        other = await make_user(db, UserRole.instructor, username="att_instr6b")
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()
        token = await _token(client, "att_instr6b")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/attendance/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_assigned_instructor_can_view_stats(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr7")
        session, _ = await _seed_live_session(db, owner.id)
        token = await _token(client, "att_instr7")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/attendance/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_admin_can_view_stats(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="att_instr8")
        session, _ = await _seed_live_session(db, owner.id)
        admin = await make_user(db, UserRole.admin, username="att_admin8")
        token = await _token(client, "att_admin8")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/attendance/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_unauthenticated_cannot_checkin(self, client, db):
        resp = await client.post(
            f"/api/v1/sessions/{uuid.uuid4()}/attendance/checkin",
            json={"learner_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401
