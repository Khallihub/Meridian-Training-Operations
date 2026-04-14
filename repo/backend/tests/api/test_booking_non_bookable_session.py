"""Regression tests for B-01: Non-bookable sessions cannot be sold or booked.

Verifies that sessions in terminal / non-scheduled states are rejected at:
  - BookingService.create (direct booking)
  - CheckoutService._get_session_price → create_cart (cart/checkout flow)
"""

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import make_user, resp_data
from app.modules.users.models import UserRole


# ---------------------------------------------------------------------------
# Shared seed helper
# ---------------------------------------------------------------------------

async def _seed_session_with_status(db, status_str: str):
    """Create the minimal graph and return (session, learner_user)."""
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session, SessionStatus

    loc = Location(name=f"B01 Site {status_str}", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="B01 Room", capacity=30)
    db.add(room)
    course = Course(title="B01 Course", price=99.0, duration_minutes=60)
    db.add(course)
    await db.flush()

    instr_user = await make_user(db, UserRole.instructor, username=f"b01_instr_{status_str}")
    instructor = Instructor(user_id=instr_user.id)
    db.add(instructor)
    await db.flush()

    now = datetime.now(UTC)
    session = Session(
        title=f"B01 Session ({status_str})",
        course_id=course.id,
        instructor_id=instructor.id,
        room_id=room.id,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        capacity=20,
        status=SessionStatus(status_str),
        created_by=instr_user.id,
    )
    db.add(session)
    await db.flush()

    learner = await make_user(db, UserRole.learner, username=f"b01_learner_{status_str}")
    return session, learner


async def _get_token(client, username: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPass@1234"},
    )
    return resp_data(resp)["access_token"]


# ---------------------------------------------------------------------------
# BookingService.create — non-bookable status → 409
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestBookingNonBookableSession:
    @pytest.mark.parametrize("bad_status", ["ended", "canceled", "draft", "live", "archived"])
    async def test_booking_rejected_for_non_scheduled_session(self, client, db, bad_status):
        """Creating a booking for a non-scheduled session must return 409."""
        session, learner = await _seed_session_with_status(db, bad_status)
        token = await _get_token(client, learner.username)

        resp = await client.post(
            "/api/v1/bookings",
            json={"session_id": str(session.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 409, (
            f"Expected 409 for status={bad_status!r}, got {resp.status_code}: {resp.text}"
        )

    async def test_booking_accepted_for_scheduled_session(self, client, db):
        """Creating a booking for a scheduled session must succeed (201)."""
        from app.modules.sessions.models import SessionStatus
        session, learner = await _seed_session_with_status(db, SessionStatus.scheduled.value)
        # Reset to future time so the session is truly schedulable
        session.start_time = datetime.now(UTC) + timedelta(days=2)
        session.end_time = datetime.now(UTC) + timedelta(days=2, hours=1)
        await db.flush()

        token = await _get_token(client, learner.username)
        resp = await client.post(
            "/api/v1/bookings",
            json={"session_id": str(session.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 201, (
            f"Expected 201 for scheduled session, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# CheckoutService.create_cart — non-bookable status → 409
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCheckoutNonBookableSession:
    @pytest.mark.parametrize("bad_status", ["ended", "canceled"])
    async def test_cart_rejected_for_non_scheduled_session(self, client, db, bad_status):
        """Creating a cart containing a non-scheduled session must return 409."""
        session, learner = await _seed_session_with_status(db, bad_status)
        token = await _get_token(client, learner.username)

        resp = await client.post(
            "/api/v1/checkout/cart",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 409, (
            f"Expected 409 for status={bad_status!r}, got {resp.status_code}: {resp.text}"
        )

    async def test_best_offer_rejected_for_non_scheduled_session(self, client, db):
        """Best-offer dry-run for a non-scheduled session must also return 409."""
        session, learner = await _seed_session_with_status(db, "ended")
        token = await _get_token(client, learner.username)

        resp = await client.post(
            "/api/v1/checkout/best-offer",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 409, (
            f"Expected 409 for best-offer on ended session, got {resp.status_code}: {resp.text}"
        )
