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

        from app.modules.sessions.models import SessionStatus
        _BOOKABLE = {SessionStatus.scheduled}
        if session.status not in _BOOKABLE:
            raise ConflictError(f"Session is not bookable (status: {session.status}).")

        if session.enrolled_count >= session.capacity:
            raise ConflictError("Session is at full capacity.")

        existing = await self._repo.get_by_learner_session(learner_id, payload.session_id)
        if existing:
            raise ConflictError("You already have an active booking for this session.")

        booking = Booking(session_id=payload.session_id, learner_id=learner_id, status=BookingStatus.requested)
        booking = await self._repo.create(booking)
        return BookingResponse.model_validate(booking)

    async def confirm(self, booking_id: uuid.UUID, actor_id: str, caller_role: str | None = None) -> BookingResponse:
        booking = await self._repo.get(booking_id)
        if not booking:
            raise NotFoundError("Booking")
        if booking.status != BookingStatus.requested:
            raise ConflictError(f"Cannot confirm booking with status {booking.status}.")

        # Instructors may only confirm bookings for sessions they own.
        # session.instructor_id is instructors.id, not users.id — must resolve via Instructor record.
        if caller_role == "instructor":
            session_check = await self._session_repo.get(booking.session_id)
            from sqlalchemy import select as _sel_i
            from app.modules.instructors.models import Instructor as _Instructor
            _instr_result = await self._db.execute(
                _sel_i(_Instructor).where(_Instructor.user_id == uuid.UUID(actor_id))
            )
            _instructor = _instr_result.scalar_one_or_none()
            if not session_check or not _instructor or session_check.instructor_id != _instructor.id:
                raise ForbiddenError("Instructors can only confirm bookings for their own sessions.")

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

        if booking.status not in (BookingStatus.requested, BookingStatus.confirmed):
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
        booking.status = BookingStatus.rescheduled_out
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

        if booking.status in (BookingStatus.canceled, BookingStatus.no_show, BookingStatus.completed, BookingStatus.rescheduled_out):
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

        booking.status = BookingStatus.canceled
        booking.cancelled_at = datetime.now(UTC)
        booking.cancellation_reason = payload.reason if payload else None
        await self._repo.save(booking)
        await log_audit(self._db, actor_id, "booking", str(booking_id), "cancel")
        return BookingResponse.model_validate(booking)

    async def list(
        self, learner_id: uuid.UUID | None, session_id: uuid.UUID | None,
        status: BookingStatus | None, page: int, page_size: int,
        instructor_id: uuid.UUID | None = None,
        finance_payment_scoped: bool = False,
    ) -> tuple[list[BookingResponse], int]:
        bookings, total = await self._repo.list(
            learner_id, session_id, status, page, page_size,
            instructor_id=instructor_id,
            finance_payment_scoped=finance_payment_scoped,
        )
        return [BookingResponse.model_validate(b) for b in bookings], total

    async def get(self, booking_id: uuid.UUID, caller_id: str | None = None, caller_role: str | None = None) -> BookingResponse:
        b = await self._repo.get(booking_id)
        if not b:
            raise NotFoundError("Booking")
        if caller_role != "admin" and caller_id and str(b.learner_id) != caller_id:
            if caller_role == "instructor":
                session = await self._session_repo.get(b.session_id)
                # session.instructor_id is instructors.id, not users.id — resolve via Instructor record.
                from sqlalchemy import select as _sel_i2
                from app.modules.instructors.models import Instructor as _Instructor2
                _instr_result2 = await self._db.execute(
                    _sel_i2(_Instructor2).where(_Instructor2.user_id == uuid.UUID(caller_id))
                )
                _instructor2 = _instr_result2.scalar_one_or_none()
                if not session or not _instructor2 or session.instructor_id != _instructor2.id:
                    raise ForbiddenError("Not your booking")
            elif caller_role == "finance":
                # Finance may access a booking only when an order exists for the same
                # learner+session, i.e. there is a payment context to justify access.
                from sqlalchemy import select, exists as _exists, and_ as _and_
                from app.modules.checkout.models import Order as _Order, OrderItem as _OrderItem
                stmt = select(_exists().where(
                    _and_(
                        _OrderItem.session_id == b.session_id,
                        _Order.learner_id == b.learner_id,
                        _OrderItem.order_id == _Order.id,
                    )
                ))
                result = await self._db.execute(stmt)
                if not result.scalar():
                    raise ForbiddenError("Not your booking")
            else:
                raise ForbiddenError("Not your booking")
        return BookingResponse.model_validate(b)
