from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnprocessableError
from app.modules.bookings.models import Booking, BookingStatus
from app.modules.bookings.repository import BookingRepository
from app.modules.bookings.schemas import (
    BookingCreate, BookingResponse, CancelRequest, RescheduleRequest,
)
from app.modules.sessions.repository import SessionRepository
from app.modules.sessions.websocket import room_manager


class BookingService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = BookingRepository(db)
        self._session_repo = SessionRepository(db)
        self._db = db

    async def create(self, payload: BookingCreate, learner_id: uuid.UUID) -> BookingResponse:
        session = await self._session_repo.get(payload.session_id)
        if not session:
            raise NotFoundError("Session")

        if session.enrolled_count >= session.capacity:
            raise ConflictError("Session is at full capacity.")

        existing = await self._repo.get_by_learner_session(learner_id, payload.session_id)
        if existing:
            raise ConflictError("You already have an active booking for this session.")

        booking = Booking(session_id=payload.session_id, learner_id=learner_id)
        booking = await self._repo.create(booking)
        return BookingResponse.model_validate(booking)

    async def confirm(self, booking_id: uuid.UUID, actor_id: str) -> BookingResponse:
        booking = await self._repo.get(booking_id)
        if not booking:
            raise NotFoundError("Booking")
        if booking.status != BookingStatus.pending:
            raise ConflictError(f"Cannot confirm booking with status {booking.status}.")

        # Re-check capacity with a row lock to prevent overbooking under concurrency
        from sqlalchemy import select as _select
        from app.modules.sessions.models import Session as _Session
        session_result = await self._db.execute(
            _select(_Session).where(_Session.id == booking.session_id).with_for_update()
        )
        session = session_result.scalar_one_or_none()
        if session and session.enrolled_count >= session.capacity:
            raise ConflictError("Session is at full capacity; booking cannot be confirmed.")

        booking.status = BookingStatus.confirmed
        booking.confirmed_at = datetime.now(UTC)
        await self._repo.save(booking)

        # Increment enrolled count
        if session:
            session.enrolled_count += 1
            await self._session_repo.save(session)
            await room_manager.broadcast(str(booking.session_id), {
                "type": "roster_update",
                "enrolled_count": session.enrolled_count,
            })

        await log_audit(self._db, actor_id, "booking", str(booking_id), "confirm")
        return BookingResponse.model_validate(booking)

    async def reschedule(self, booking_id: uuid.UUID, payload: RescheduleRequest, actor_id: str, caller_role: str | None = None) -> BookingResponse:
        booking = await self._repo.get(booking_id)
        if not booking:
            raise NotFoundError("Booking")
        if caller_role != "admin" and str(booking.learner_id) != actor_id:
            raise ForbiddenError("Not your booking")

        if booking.status not in (BookingStatus.pending, BookingStatus.confirmed):
            raise ConflictError(f"Cannot reschedule booking with status {booking.status}.")

        from app.modules.policy.service import get_policy
        policy = await get_policy(self._db)
        session = await self._session_repo.get(booking.session_id)
        if session and (session.start_time - datetime.now(UTC)) < timedelta(hours=policy.reschedule_cutoff_hours):
            raise UnprocessableError(
                f"Reschedule is blocked within {policy.reschedule_cutoff_hours} hours of session start."
            )

        new_session = await self._session_repo.get(payload.new_session_id)
        if not new_session:
            raise NotFoundError("New session")
        if new_session.enrolled_count >= new_session.capacity:
            raise ConflictError("Target session is at full capacity.")

        # Decrement old session count if confirmed
        if booking.status == BookingStatus.confirmed and session:
            session.enrolled_count = max(0, session.enrolled_count - 1)
            await self._session_repo.save(session)

        old_session_id = booking.session_id
        booking.rescheduled_from_id = booking.id
        booking.session_id = payload.new_session_id
        booking.status = BookingStatus.rescheduled
        await self._repo.save(booking)

        # Increment new session count
        new_session.enrolled_count += 1
        await self._session_repo.save(new_session)

        await log_audit(self._db, actor_id, "booking", str(booking_id), "reschedule",
                        old_value={"session_id": str(old_session_id)},
                        new_value={"session_id": str(payload.new_session_id)})
        return BookingResponse.model_validate(booking)

    async def cancel(self, booking_id: uuid.UUID, payload: CancelRequest, actor_id: str, caller_role: str | None = None) -> BookingResponse:
        booking = await self._repo.get(booking_id)
        if not booking:
            raise NotFoundError("Booking")
        if caller_role != "admin" and str(booking.learner_id) != actor_id:
            raise ForbiddenError("Not your booking")

        if booking.status in (BookingStatus.cancelled, BookingStatus.no_show):
            raise ConflictError(f"Booking already in terminal state: {booking.status}.")

        learner_initiated = caller_role == "learner"
        # Policy-configurable cancellation fee window (learner-initiated only)
        from app.modules.policy.service import get_policy
        policy = await get_policy(self._db)
        session = await self._session_repo.get(booking.session_id)
        if learner_initiated and session:
            if (session.start_time - datetime.now(UTC)) < timedelta(hours=policy.cancellation_fee_hours):
                booking.policy_fee_flagged = True

        if booking.status == BookingStatus.confirmed and session:
            session.enrolled_count = max(0, session.enrolled_count - 1)
            await self._session_repo.save(session)
            await room_manager.broadcast(str(booking.session_id), {
                "type": "roster_update",
                "enrolled_count": session.enrolled_count,
            })

        booking.status = BookingStatus.cancelled
        booking.cancelled_at = datetime.now(UTC)
        booking.cancellation_reason = payload.reason if payload else None
        await self._repo.save(booking)
        await log_audit(self._db, actor_id, "booking", str(booking_id), "cancel")
        return BookingResponse.model_validate(booking)

    async def list(
        self, learner_id: uuid.UUID | None, session_id: uuid.UUID | None,
        status: BookingStatus | None, page: int, page_size: int
    ) -> tuple[list[BookingResponse], int]:
        bookings, total = await self._repo.list(learner_id, session_id, status, page, page_size)
        return [BookingResponse.model_validate(b) for b in bookings], total

    async def get(self, booking_id: uuid.UUID, caller_id: str | None = None, caller_role: str | None = None) -> BookingResponse:
        b = await self._repo.get(booking_id)
        if not b:
            raise NotFoundError("Booking")
        if caller_role not in ("admin", "finance", "dataops") and caller_id and str(b.learner_id) != caller_id:
            raise ForbiddenError("Not your booking")
        return BookingResponse.model_validate(b)
