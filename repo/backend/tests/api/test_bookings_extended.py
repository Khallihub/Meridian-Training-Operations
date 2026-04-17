"""API tests for additional booking endpoints: list, history, confirm, reschedule, cancel."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _seed_session(db):
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session

    loc = Location(name="Bk Site", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Bk Room", capacity=30)
    db.add(room)
    course = Course(title="Bk Course", price=100.0, duration_minutes=60)
    db.add(course)
    await db.flush()
    instr_user = await make_user(db, UserRole.instructor, username="bk_instr")
    instr = Instructor(user_id=instr_user.id)
    db.add(instr)
    await db.flush()
    now = datetime.now(UTC)
    session = Session(
        title="Bk Session",
        course_id=course.id, instructor_id=instr.id, room_id=room.id,
        start_time=now + timedelta(days=5), end_time=now + timedelta(days=5, hours=1),
        capacity=20, created_by=instr_user.id,
    )
    db.add(session)
    await db.flush()
    return session, instr, instr_user


async def _seed_second_session(db, instr, instr_user):
    """Create a second session for reschedule target."""
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.sessions.models import Session

    loc = Location(name="Bk Site2", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Bk Room2", capacity=30)
    db.add(room)
    course = Course(title="Bk Course2", price=100.0)
    db.add(course)
    await db.flush()
    now = datetime.now(UTC)
    session = Session(
        title="Bk Session Reschedule Target",
        course_id=course.id, instructor_id=instr.id, room_id=room.id,
        start_time=now + timedelta(days=10), end_time=now + timedelta(days=10, hours=1),
        capacity=20, created_by=instr_user.id,
    )
    db.add(session)
    await db.flush()
    return session


@pytest.mark.asyncio
class TestBookingsList:
    async def test_admin_can_list_bookings(self, client, db):
        session, instr, instr_user = await _seed_session(db)
        admin = await make_user(db, UserRole.admin, username="bk_admin1")
        token = await get_token(client, "bk_admin1")
        resp = await client.get("/api/v1/bookings", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_learner_lists_own_bookings(self, client, db):
        session, instr, instr_user = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="bk_learner1")
        token = await get_token(client, "bk_learner1")

        # Create a booking
        await client.post(
            "/api/v1/bookings",
            json={"session_id": str(session.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get("/api/v1/bookings", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestBookingHistory:
    async def test_admin_can_view_booking_history(self, client, db):
        session, instr, instr_user = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="bk_hist_learner")
        admin = await make_user(db, UserRole.admin, username="bk_hist_admin")
        learner_token = await get_token(client, "bk_hist_learner")
        admin_token = await get_token(client, "bk_hist_admin")

        # Create booking
        book_resp = await client.post(
            "/api/v1/bookings",
            json={"session_id": str(session.id)},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        booking_id = resp_data(book_resp)["id"]

        resp = await client.get(
            f"/api/v1/bookings/{booking_id}/history",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)


@pytest.mark.asyncio
class TestBookingConfirm:
    async def test_admin_can_confirm_booking(self, client, db):
        session, instr, instr_user = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="bk_cnf_learner")
        admin = await make_user(db, UserRole.admin, username="bk_cnf_admin")
        learner_token = await get_token(client, "bk_cnf_learner")
        admin_token = await get_token(client, "bk_cnf_admin")

        book_resp = await client.post(
            "/api/v1/bookings",
            json={"session_id": str(session.id)},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        booking_id = resp_data(book_resp)["id"]

        resp = await client.patch(
            f"/api/v1/bookings/{booking_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["status"] == "confirmed"


@pytest.mark.asyncio
class TestBookingRescheduleCancel:
    async def test_reschedule_booking(self, client, db):
        session, instr, instr_user = await _seed_session(db)
        session2 = await _seed_second_session(db, instr, instr_user)
        learner = await make_user(db, UserRole.learner, username="bk_resc_learner")
        admin = await make_user(db, UserRole.admin, username="bk_resc_admin")
        learner_token = await get_token(client, "bk_resc_learner")
        admin_token = await get_token(client, "bk_resc_admin")

        book_resp = await client.post(
            "/api/v1/bookings",
            json={"session_id": str(session.id)},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        booking_id = resp_data(book_resp)["id"]

        # Confirm first
        await client.patch(
            f"/api/v1/bookings/{booking_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await client.post(
            f"/api/v1/bookings/{booking_id}/reschedule",
            json={"new_session_id": str(session2.id)},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["status"] in ("rescheduled_out", "confirmed", "requested")

    async def test_cancel_booking(self, client, db):
        session, instr, instr_user = await _seed_session(db)
        learner = await make_user(db, UserRole.learner, username="bk_cancel_learner")
        admin = await make_user(db, UserRole.admin, username="bk_cancel_admin")
        learner_token = await get_token(client, "bk_cancel_learner")
        admin_token = await get_token(client, "bk_cancel_admin")

        book_resp = await client.post(
            "/api/v1/bookings",
            json={"session_id": str(session.id)},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        booking_id = resp_data(book_resp)["id"]

        # Confirm first
        await client.patch(
            f"/api/v1/bookings/{booking_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await client.post(
            f"/api/v1/bookings/{booking_id}/cancel",
            json={"reason": "Schedule conflict"},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["status"] == "canceled"
