import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.bookings.models import Booking, BookingStatus


def _with_relations(q):
    return q.options(selectinload(Booking.session), selectinload(Booking.learner))


class BookingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, booking_id: uuid.UUID) -> Booking | None:
        result = await self._db.execute(
            _with_relations(select(Booking)).where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()

    async def get_by_learner_session(self, learner_id: uuid.UUID, session_id: uuid.UUID) -> Booking | None:
        result = await self._db.execute(
            select(Booking).where(
                and_(Booking.learner_id == learner_id, Booking.session_id == session_id,
                     Booking.status.not_in([BookingStatus.cancelled]))
            )
        )
        return result.scalar_one_or_none()

    async def create(self, booking: Booking) -> Booking:
        self._db.add(booking)
        await self._db.flush()
        await self._db.refresh(booking)
        return booking

    async def save(self, obj) -> None:
        await self._db.flush()

    async def list(
        self, learner_id: uuid.UUID | None, session_id: uuid.UUID | None,
        status: BookingStatus | None, page: int, page_size: int
    ) -> tuple[list[Booking], int]:
        from sqlalchemy import func
        q = select(Booking)
        if learner_id:
            q = q.where(Booking.learner_id == learner_id)
        if session_id:
            q = q.where(Booking.session_id == session_id)
        if status:
            q = q.where(Booking.status == status)

        count_result = await self._db.execute(select(func.count()).select_from(q.subquery()))
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self._db.execute(
            _with_relations(q).order_by(Booking.created_at.desc()).offset(offset).limit(page_size)
        )
        return result.scalars().all(), total
