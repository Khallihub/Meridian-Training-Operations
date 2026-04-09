from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.attendance.models import AttendanceRecord
from app.modules.attendance.schemas import (
    AttendanceRecordResponse, AttendanceStats, CheckInRequest, CheckOutRequest,
)
from app.modules.replays.models import ReplayView
from app.modules.sessions.repository import SessionRepository
from app.modules.sessions.websocket import room_manager


class AttendanceService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._session_repo = SessionRepository(db)

    async def checkin(self, session_id: uuid.UUID, payload: CheckInRequest) -> AttendanceRecordResponse:
        session = await self._session_repo.get(session_id)
        if not session:
            raise NotFoundError("Session")

        # Require a confirmed booking
        from app.modules.bookings.models import Booking, BookingStatus
        from app.core.exceptions import ForbiddenError
        booking_result = await self._db.execute(
            select(Booking).where(
                and_(
                    Booking.session_id == session_id,
                    Booking.learner_id == payload.learner_id,
                    Booking.status == BookingStatus.confirmed,
                )
            )
        )
        if not booking_result.scalar_one_or_none():
            raise ForbiddenError("Learner does not have a confirmed booking for this session.")

        # Check if already checked in
        result = await self._db.execute(
            select(AttendanceRecord).where(
                and_(AttendanceRecord.session_id == session_id, AttendanceRecord.learner_id == payload.learner_id)
            )
        )
        record = result.scalar_one_or_none()
        if record and record.joined_at:
            raise ConflictError("Learner already checked in.")

        now = datetime.now(UTC)
        was_late = session.start_time and now > session.start_time

        if record:
            record.joined_at = now
            record.was_late = was_late
        else:
            record = AttendanceRecord(
                session_id=session_id,
                learner_id=payload.learner_id,
                joined_at=now,
                was_late=was_late,
            )
            self._db.add(record)
        await self._db.flush()

        await room_manager.broadcast(str(session_id), {
            "type": "attendee_joined",
            "learner_id": str(payload.learner_id),
        })

        return AttendanceRecordResponse.model_validate(record)

    async def checkout(self, session_id: uuid.UUID, payload: CheckOutRequest) -> AttendanceRecordResponse:
        result = await self._db.execute(
            select(AttendanceRecord).where(
                and_(AttendanceRecord.session_id == session_id, AttendanceRecord.learner_id == payload.learner_id)
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise NotFoundError("Attendance record")

        now = datetime.now(UTC)
        record.left_at = now
        if record.joined_at:
            delta = now - record.joined_at
            record.minutes_attended = int(delta.total_seconds() / 60)
        await self._db.flush()

        await room_manager.broadcast(str(session_id), {
            "type": "attendee_left",
            "learner_id": str(payload.learner_id),
        })

        return AttendanceRecordResponse.model_validate(record)

    async def get_stats(self, session_id: uuid.UUID) -> AttendanceStats:
        session = await self._session_repo.get(session_id)
        if not session:
            raise NotFoundError("Session")

        records_result = await self._db.execute(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
        )
        records = records_result.scalars().all()

        checked_in = sum(1 for r in records if r.joined_at)
        late_joins = sum(1 for r in records if r.was_late)
        avg_minutes = (
            sum(r.minutes_attended for r in records if r.minutes_attended) / len(records)
            if records else 0.0
        )

        # Replay completion rate
        replay_result = await self._db.execute(
            select(func.count()).where(
                and_(ReplayView.session_id == session_id, ReplayView.completed == True)
            )
        )
        completed_views = replay_result.scalar_one()
        total_views_result = await self._db.execute(
            select(func.count()).where(ReplayView.session_id == session_id)
        )
        total_views = total_views_result.scalar_one()
        replay_completion = (completed_views / total_views * 100) if total_views else 0.0

        return AttendanceStats(
            session_id=session_id,
            total_enrolled=session.enrolled_count,
            checked_in=checked_in,
            late_joins=late_joins,
            avg_minutes_attended=round(avg_minutes, 1),
            replay_completion_rate=round(replay_completion, 1),
        )
