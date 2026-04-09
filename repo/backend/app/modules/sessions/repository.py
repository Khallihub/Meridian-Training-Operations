from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.models import RecurrenceRule, Session, SessionStatus


def _session_joins():
    """Standard joinedload options to populate computed properties."""
    from app.modules.instructors.models import Instructor
    from app.modules.locations.models import Room
    return [
        joinedload(Session.course),
        joinedload(Session.instructor).joinedload(Instructor.user),
        joinedload(Session.room).joinedload(Room.location),
    ]


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: uuid.UUID) -> Session | None:
        result = await self._db.execute(
            select(Session)
            .where(Session.id == session_id)
            .options(*_session_joins())
        )
        return result.unique().scalar_one_or_none()

    async def create(self, session: Session) -> Session:
        self._db.add(session)
        await self._db.flush()
        # Re-fetch with joins so computed properties are available
        return await self.get(session.id)

    async def create_recurrence_rule(self, rule: RecurrenceRule) -> RecurrenceRule:
        self._db.add(rule)
        await self._db.flush()
        await self._db.refresh(rule)
        return rule

    async def save(self, obj) -> None:
        await self._db.flush()

    async def list_weekly(
        self, week_start: datetime, week_end: datetime,
        location_id: uuid.UUID | None, instructor_id: uuid.UUID | None,
    ) -> list[Session]:
        q = (
            select(Session)
            .where(and_(Session.start_time >= week_start, Session.start_time < week_end))
            .options(*_session_joins())
        )
        if instructor_id:
            q = q.where(Session.instructor_id == instructor_id)
        if location_id:
            from app.modules.locations.models import Room
            q = q.join(Room, Session.room_id == Room.id).where(Room.location_id == location_id)
        result = await self._db.execute(q.order_by(Session.start_time))
        return result.scalars().unique().all()

    async def list_monthly(
        self, month_start: datetime, month_end: datetime,
        location_id: uuid.UUID | None, instructor_id: uuid.UUID | None,
    ) -> list[Session]:
        return await self.list_weekly(month_start, month_end, location_id, instructor_id)

    async def get_enrolled_learners(self, session_id: uuid.UUID) -> list:
        from app.modules.attendance.models import AttendanceRecord
        from app.modules.bookings.models import Booking, BookingStatus

        bookings_result = await self._db.execute(
            select(Booking)
            .where(and_(Booking.session_id == session_id, Booking.status == BookingStatus.confirmed))
            .options(joinedload(Booking.learner))
        )
        bookings = bookings_result.scalars().all()

        attendance_result = await self._db.execute(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
        )
        att_by_learner = {str(a.learner_id): a for a in attendance_result.scalars().all()}

        roster = []
        for b in bookings:
            u = b.learner
            att = att_by_learner.get(str(u.id))
            roster.append({
                "id": str(u.id),
                "username": u.username,
                "checked_in": att is not None and att.joined_at is not None,
                "checked_out": att is not None and att.left_at is not None,
            })
        return roster
