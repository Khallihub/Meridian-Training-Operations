from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone

from dateutil.rrule import rrulestr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.modules.sessions.models import RecurrenceRule, Session, SessionStatus
from app.modules.sessions.repository import SessionRepository
from app.modules.sessions.schemas import (
    RecurringSessionCreate, SessionCreate, SessionResponse, SessionUpdate,
)
from app.modules.sessions.websocket import room_manager


def _to_tz(dt: datetime, tz_name: str) -> datetime:
    import zoneinfo
    tz = zoneinfo.ZoneInfo(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = SessionRepository(db)
        self._db = db

    async def _check_room_conflict(
        self,
        room_id: uuid.UUID,
        start: datetime,
        end: datetime,
        buffer_minutes: int,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        from sqlalchemy import and_, or_, select
        buffered_end = end + timedelta(minutes=buffer_minutes)
        q = (
            select(Session)
            .where(Session.room_id == room_id)
            .where(Session.status != SessionStatus.cancelled)
            .where(and_(Session.start_time < buffered_end, Session.end_time > start))
        )
        if exclude_id:
            q = q.where(Session.id != exclude_id)
        result = await self._db.execute(q)
        conflict = result.scalar_one_or_none()
        if conflict:
            raise ConflictError(
                f"Room conflict: session already scheduled {conflict.start_time}–{conflict.end_time} (including buffer)."
            )

    async def create(self, payload: SessionCreate, created_by: uuid.UUID) -> SessionResponse:
        await self._check_room_conflict(
            payload.room_id, payload.start_time, payload.end_time, payload.buffer_minutes
        )
        session = Session(**payload.model_dump(), created_by=created_by)
        session = await self._repo.create(session)
        await log_audit(self._db, str(created_by), "session", str(session.id), "create")
        return SessionResponse.model_validate(session)

    async def _fresh(self, session_id: uuid.UUID) -> SessionResponse:
        """Re-fetch with all joins and return a serialisable response."""
        s = await self._repo.get(session_id)
        return SessionResponse.model_validate(s)

    async def create_recurring(self, payload: RecurringSessionCreate, created_by: uuid.UUID) -> list[SessionResponse]:
        rule = RecurrenceRule(
            rrule_string=payload.recurrence.rrule_string,
            start_date=payload.recurrence.start_date,
            end_date=payload.recurrence.end_date,
        )
        rule = await self._repo.create_recurrence_rule(rule)

        # Expand RRULE dates
        try:
            rr = rrulestr(payload.recurrence.rrule_string, dtstart=payload.recurrence.start_date)
        except Exception as e:
            raise UnprocessableError(f"Invalid RRULE string: {e}")

        until = payload.recurrence.end_date or (payload.recurrence.start_date + timedelta(days=365))
        dates = list(rr.between(payload.recurrence.start_date, until, inc=True))

        sessions = []
        for dt in dates:
            # Determine duration from course
            from sqlalchemy import select
            from app.modules.courses.models import Course
            course_result = await self._db.execute(select(Course).where(Course.id == payload.course_id))
            course = course_result.scalar_one_or_none()
            duration = course.duration_minutes if course else 60
            end_dt = dt + timedelta(minutes=duration)

            await self._check_room_conflict(payload.room_id, dt, end_dt, payload.buffer_minutes)
            s = Session(
                title=payload.title,
                course_id=payload.course_id,
                instructor_id=payload.instructor_id,
                room_id=payload.room_id,
                start_time=dt,
                end_time=end_dt,
                capacity=payload.capacity,
                buffer_minutes=payload.buffer_minutes,
                recurrence_rule_id=rule.id,
                created_by=created_by,
            )
            s = await self._repo.create(s)
            sessions.append(await self._fresh(s.id))

        return sessions

    async def get(self, session_id: uuid.UUID) -> SessionResponse:
        s = await self._repo.get(session_id)
        if not s:
            raise NotFoundError("Session")
        return await self._fresh(session_id)

    async def list_weekly(
        self, week_str: str, tz_name: str = "UTC",
        location_id: uuid.UUID | None = None, instructor_id: uuid.UUID | None = None,
    ) -> list[SessionResponse]:
        # week_str: "2026-W14"
        import zoneinfo
        tz = zoneinfo.ZoneInfo(tz_name)
        year, week = int(week_str.split("-W")[0]), int(week_str.split("-W")[1])
        week_start = datetime.fromisocalendar(year, week, 1).replace(hour=0, minute=0, second=0, tzinfo=tz)
        week_end = week_start + timedelta(days=7)
        sessions = await self._repo.list_weekly(week_start, week_end, location_id, instructor_id)
        return [SessionResponse.model_validate(s) for s in sessions]

    async def list_monthly(
        self, month_str: str, tz_name: str = "UTC",
        location_id: uuid.UUID | None = None, instructor_id: uuid.UUID | None = None,
    ) -> list[SessionResponse]:
        import zoneinfo, calendar
        tz = zoneinfo.ZoneInfo(tz_name)
        year, month = int(month_str.split("-")[0]), int(month_str.split("-")[1])
        month_start = datetime(year, month, 1, tzinfo=tz)
        _, last_day = calendar.monthrange(year, month)
        month_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=tz)
        sessions = await self._repo.list_monthly(month_start, month_end, location_id, instructor_id)
        return [SessionResponse.model_validate(s) for s in sessions]

    async def update(self, session_id: uuid.UUID, payload: SessionUpdate, actor_id: str) -> SessionResponse:
        s = await self._repo.get(session_id)
        if not s:
            raise NotFoundError("Session")
        old = {"status": s.status, "start_time": str(s.start_time)}
        updates = payload.model_dump(exclude_none=True)
        if any(k in updates for k in ("room_id", "start_time", "end_time")):
            room_id = updates.get("room_id", s.room_id)
            start = updates.get("start_time", s.start_time)
            end = updates.get("end_time", s.end_time)
            buffer = updates.get("buffer_minutes", s.buffer_minutes)
            await self._check_room_conflict(room_id, start, end, buffer, exclude_id=session_id)
        for k, v in updates.items():
            setattr(s, k, v)
        await self._repo.save(s)
        await log_audit(self._db, actor_id, "session", str(session_id), "update", old, payload.model_dump(exclude_none=True))
        return await self._fresh(session_id)

    async def cancel(self, session_id: uuid.UUID, actor_id: str) -> SessionResponse:
        s = await self._repo.get(session_id)
        if not s:
            raise NotFoundError("Session")
        if s.status == SessionStatus.completed:
            raise ConflictError("Cannot cancel a completed session.")
        s.status = SessionStatus.cancelled
        await self._repo.save(s)
        await log_audit(self._db, actor_id, "session", str(session_id), "cancel")
        await room_manager.broadcast(str(session_id), {"type": "session_status_changed", "status": "cancelled"})
        return await self._fresh(session_id)

    async def go_live(self, session_id: uuid.UUID, actor_id: str) -> SessionResponse:
        s = await self._repo.get(session_id)
        if not s:
            raise NotFoundError("Session")
        if s.status != SessionStatus.scheduled:
            raise ConflictError(f"Session is {s.status}, cannot go live.")
        s.status = SessionStatus.live
        await self._repo.save(s)
        await room_manager.broadcast(str(session_id), {"type": "session_status_changed", "status": "live"})
        return await self._fresh(session_id)

    async def complete(self, session_id: uuid.UUID, actor_id: str) -> SessionResponse:
        s = await self._repo.get(session_id)
        if not s:
            raise NotFoundError("Session")
        if s.status != SessionStatus.live:
            raise ConflictError("Session must be live to complete.")
        s.status = SessionStatus.completed
        await self._repo.save(s)
        await room_manager.broadcast(str(session_id), {"type": "session_status_changed", "status": "completed"})
        return await self._fresh(session_id)

    async def get_roster(self, session_id: uuid.UUID) -> list:
        s = await self._repo.get(session_id)
        if not s:
            raise NotFoundError("Session")
        return await self._repo.get_enrolled_learners(session_id)

    async def delete(self, session_id: uuid.UUID, actor_id: str) -> None:
        s = await self._repo.get(session_id)
        if not s:
            raise NotFoundError("Session")
        s.status = SessionStatus.cancelled
        await self._repo.save(s)
        await log_audit(self._db, actor_id, "session", str(session_id), "delete")
