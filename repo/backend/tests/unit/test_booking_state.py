"""Unit tests for booking state transition rules."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConflictError, UnprocessableError
from app.modules.bookings.models import Booking, BookingStatus
from app.modules.bookings.schemas import CancelRequest, RescheduleRequest
from app.modules.sessions.models import Session, SessionStatus


def make_booking(status=BookingStatus.confirmed):
    b = Booking()
    b.id = uuid.uuid4()
    b.session_id = uuid.uuid4()
    b.learner_id = uuid.uuid4()
    b.status = status
    b.policy_fee_flagged = False
    return b


def make_session(start_offset_hours: float = 3.0):
    s = Session()
    s.id = uuid.uuid4()
    s.start_time = datetime.now(UTC) + timedelta(hours=start_offset_hours)
    s.enrolled_count = 5
    s.capacity = 20
    s.status = SessionStatus.scheduled
    return s


class TestBookingRescheduleBlocking:
    @pytest.mark.asyncio
    async def test_reschedule_blocked_within_2_hours(self, db):
        from app.modules.bookings.service import BookingService
        svc = BookingService(db)

        booking = make_booking(BookingStatus.confirmed)
        session = make_session(start_offset_hours=1)  # 1 hour away — blocked

        svc._repo = AsyncMock()
        svc._repo.get = AsyncMock(return_value=booking)
        svc._session_repo = AsyncMock()
        svc._session_repo.get = AsyncMock(return_value=session)

        with pytest.raises(UnprocessableError, match="2 hours"):
            await svc.reschedule(booking.id, RescheduleRequest(new_session_id=uuid.uuid4()), str(booking.learner_id), caller_role="learner")

    @pytest.mark.asyncio
    async def test_reschedule_allowed_outside_2_hours(self, db):
        from app.modules.bookings.service import BookingService
        svc = BookingService(db)

        booking = make_booking(BookingStatus.confirmed)
        session = make_session(start_offset_hours=5)  # 5 hours away — OK
        new_session = make_session(start_offset_hours=48)

        svc._repo = AsyncMock()
        svc._repo.get = AsyncMock(return_value=booking)
        svc._repo.save = AsyncMock()
        svc._session_repo = AsyncMock()
        svc._session_repo.get = AsyncMock(side_effect=[session, new_session])
        svc._session_repo.save = AsyncMock()

        with patch("app.modules.bookings.service.log_audit", AsyncMock()):
            with patch("app.modules.bookings.service.room_manager") as rm:
                rm.broadcast = AsyncMock()
                result = await svc.reschedule(booking.id, RescheduleRequest(new_session_id=new_session.id), str(booking.learner_id), caller_role="learner")

        assert result.status == BookingStatus.rescheduled


class TestCancellationPolicyFee:
    @pytest.mark.asyncio
    async def test_cancellation_within_24h_flags_fee(self, db):
        from app.modules.bookings.service import BookingService
        svc = BookingService(db)

        booking = make_booking(BookingStatus.confirmed)
        session = make_session(start_offset_hours=12)  # within 24h

        svc._repo = AsyncMock()
        svc._repo.get = AsyncMock(return_value=booking)
        svc._repo.save = AsyncMock()
        svc._session_repo = AsyncMock()
        svc._session_repo.get = AsyncMock(return_value=session)
        svc._session_repo.save = AsyncMock()

        with patch("app.modules.bookings.service.log_audit", AsyncMock()):
            with patch("app.modules.bookings.service.room_manager") as rm:
                rm.broadcast = AsyncMock()
                result = await svc.cancel(booking.id, CancelRequest(), str(booking.learner_id), caller_role="learner")

        assert result.policy_fee_flagged is True

    @pytest.mark.asyncio
    async def test_cancellation_outside_24h_no_fee(self, db):
        from app.modules.bookings.service import BookingService
        svc = BookingService(db)

        booking = make_booking(BookingStatus.confirmed)
        session = make_session(start_offset_hours=48)  # outside 24h

        svc._repo = AsyncMock()
        svc._repo.get = AsyncMock(return_value=booking)
        svc._repo.save = AsyncMock()
        svc._session_repo = AsyncMock()
        svc._session_repo.get = AsyncMock(return_value=session)
        svc._session_repo.save = AsyncMock()

        with patch("app.modules.bookings.service.log_audit", AsyncMock()):
            with patch("app.modules.bookings.service.room_manager") as rm:
                rm.broadcast = AsyncMock()
                result = await svc.cancel(booking.id, CancelRequest(), str(booking.learner_id), caller_role="learner")

        assert result.policy_fee_flagged is False
