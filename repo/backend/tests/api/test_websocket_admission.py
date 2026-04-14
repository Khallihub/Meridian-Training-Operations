"""Regression tests for H-01: WebSocket room admission matrix.

Tests the object-level authorization logic in session_room_ws by calling the
route handler directly with a mock WebSocket, bypassing the HTTP/WS protocol
layer.  This avoids needing a live WebSocket connection while still exercising
the exact DB queries and close-code logic introduced to close H-01.

Admission matrix under test:
  ✓ Assigned instructor          → admitted (ws.accept() called, no 4003)
  ✗ Instructor with no record    → rejected (ws.close(code=4003))
  ✗ Unassigned instructor        → rejected (ws.close(code=4003))
  ✓ Admin                        → admitted unconditionally
  ✓ Enrolled learner (confirmed) → admitted
  ✗ Unenrolled learner           → rejected (ws.close(code=4003))
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.conftest import make_user
from app.modules.users.models import UserRole


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------

async def _seed_ws_session(db):
    """Return (session, assigned_user, unassigned_user, no_record_user)."""
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session

    loc = Location(name="WS Admission Site", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="WS Room", capacity=30)
    db.add(room)
    course = Course(title="WS Course", price=50.0, duration_minutes=60)
    db.add(course)
    await db.flush()

    assigned_user = await make_user(db, UserRole.instructor, username="ws_admit_assigned")
    unassigned_user_no_rec = await make_user(db, UserRole.instructor, username="ws_admit_no_rec")
    unassigned_user_diff = await make_user(db, UserRole.instructor, username="ws_admit_diff")

    # Only `assigned_user` gets an Instructor record linked to the session
    instr = Instructor(user_id=assigned_user.id)
    db.add(instr)
    # `unassigned_user_diff` gets an Instructor record but for a different session
    instr_diff = Instructor(user_id=unassigned_user_diff.id)
    db.add(instr_diff)
    await db.flush()

    now = datetime.now(UTC)
    session = Session(
        title="WS Admission Session",
        course_id=course.id,
        instructor_id=instr.id,
        room_id=room.id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, hours=1),
        capacity=20,
        created_by=assigned_user.id,
    )
    db.add(session)
    await db.flush()

    return session, assigned_user, unassigned_user_no_rec, unassigned_user_diff


def _make_ws(disconnects_after_accept: bool = True) -> AsyncMock:
    """Create a mock WebSocket.

    For success-path tests `receive_text` raises WebSocketDisconnect so the
    handler's message loop exits cleanly.  For rejection tests the handler
    never reaches the loop, so the side-effect doesn't matter.
    """
    ws = AsyncMock()
    if disconnects_after_accept:
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect(code=1000))
    return ws


def _was_rejected_4003(mock_ws: AsyncMock) -> bool:
    """Return True if websocket.close(code=4003) was called."""
    for call in mock_ws.close.call_args_list:
        code = call.kwargs.get("code") or (call.args[0] if call.args else None)
        if code == 4003:
            return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestWebSocketAdmissionMatrix:
    # ------------------------------------------------------------------ #
    # Rejection cases                                                      #
    # ------------------------------------------------------------------ #

    async def test_instructor_without_record_rejected(self, db):
        """An instructor user with no Instructor row is rejected (4003)."""
        session, _, no_rec_user, _ = await _seed_ws_session(db)
        mock_ws = _make_ws()

        with patch("app.modules.sessions.websocket.get_ws_user", return_value=no_rec_user):
            from app.modules.sessions.websocket import session_room_ws
            await session_room_ws(str(session.id), mock_ws, db)

        assert _was_rejected_4003(mock_ws), "Expected ws.close(code=4003) for instructor with no record"

    async def test_instructor_assigned_to_different_session_rejected(self, db):
        """An instructor with a valid Instructor record but not owning the
        session is rejected (4003)."""
        session, _, _, diff_user = await _seed_ws_session(db)
        mock_ws = _make_ws()

        with patch("app.modules.sessions.websocket.get_ws_user", return_value=diff_user):
            from app.modules.sessions.websocket import session_room_ws
            await session_room_ws(str(session.id), mock_ws, db)

        assert _was_rejected_4003(mock_ws), "Expected ws.close(code=4003) for unassigned instructor"

    async def test_unenrolled_learner_rejected(self, db):
        """A learner with no confirmed booking for the session is rejected (4003)."""
        session, _, _, _ = await _seed_ws_session(db)
        learner = await make_user(db, UserRole.learner, username="ws_learner_no_booking")
        mock_ws = _make_ws()

        with patch("app.modules.sessions.websocket.get_ws_user", return_value=learner):
            from app.modules.sessions.websocket import session_room_ws
            await session_room_ws(str(session.id), mock_ws, db)

        assert _was_rejected_4003(mock_ws), "Expected ws.close(code=4003) for unenrolled learner"

    # ------------------------------------------------------------------ #
    # Admission cases                                                      #
    # ------------------------------------------------------------------ #

    async def test_assigned_instructor_admitted(self, db):
        """The instructor who owns the session is admitted."""
        session, assigned_user, _, _ = await _seed_ws_session(db)
        mock_ws = _make_ws()

        with patch("app.modules.sessions.websocket.get_ws_user", return_value=assigned_user), \
             patch("app.modules.sessions.websocket.room_manager.broadcast", new_callable=AsyncMock), \
             patch("app.modules.sessions.websocket.room_manager.send_state_snapshot", new_callable=AsyncMock):
            from app.modules.sessions.websocket import session_room_ws
            await session_room_ws(str(session.id), mock_ws, db)

        assert not _was_rejected_4003(mock_ws), "Assigned instructor should NOT be rejected"
        mock_ws.accept.assert_called_once()

    async def test_admin_admitted_unconditionally(self, db):
        """Admin bypasses all ownership checks and is always admitted."""
        session, _, _, _ = await _seed_ws_session(db)
        admin = await make_user(db, UserRole.admin, username="ws_admin_user")
        mock_ws = _make_ws()

        with patch("app.modules.sessions.websocket.get_ws_user", return_value=admin), \
             patch("app.modules.sessions.websocket.room_manager.broadcast", new_callable=AsyncMock), \
             patch("app.modules.sessions.websocket.room_manager.send_state_snapshot", new_callable=AsyncMock):
            from app.modules.sessions.websocket import session_room_ws
            await session_room_ws(str(session.id), mock_ws, db)

        assert not _was_rejected_4003(mock_ws), "Admin should NOT be rejected"
        mock_ws.accept.assert_called_once()

    async def test_enrolled_learner_admitted(self, db):
        """A learner with a confirmed booking for the session is admitted."""
        from app.modules.bookings.models import Booking, BookingStatus

        session, _, _, _ = await _seed_ws_session(db)
        learner = await make_user(db, UserRole.learner, username="ws_learner_booked")

        booking = Booking(
            session_id=session.id,
            learner_id=learner.id,
            status=BookingStatus.confirmed,
        )
        db.add(booking)
        await db.flush()

        mock_ws = _make_ws()

        with patch("app.modules.sessions.websocket.get_ws_user", return_value=learner), \
             patch("app.modules.sessions.websocket.room_manager.broadcast", new_callable=AsyncMock), \
             patch("app.modules.sessions.websocket.room_manager.send_state_snapshot", new_callable=AsyncMock):
            from app.modules.sessions.websocket import session_room_ws
            await session_room_ws(str(session.id), mock_ws, db)

        assert not _was_rejected_4003(mock_ws), "Enrolled learner should NOT be rejected"
        mock_ws.accept.assert_called_once()
