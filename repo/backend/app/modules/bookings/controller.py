import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.pagination import Page, PageMeta
from app.modules.bookings.models import BookingStatus
from app.modules.bookings.schemas import (
    BookingCreate, BookingResponse, CancelRequest, RescheduleRequest,
)
from app.modules.bookings.service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking(
    body: BookingCreate,
    current_user=Depends(require_roles("learner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    learner_id = current_user.id
    return await BookingService(db).create(body, learner_id)


@router.get("", response_model=Page[BookingResponse])
async def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session_id: uuid.UUID | None = None,
    status: BookingStatus | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    learner_id = None if current_user.role in ("admin", "instructor", "finance") else current_user.id
    items, total = await BookingService(db).list(learner_id, session_id, status, page, page_size)
    return Page(items=items, meta=PageMeta(total_count=total, page=page, page_size=page_size, has_next=(page * page_size < total)))


@router.get("/{booking_id}/history")
async def get_booking_history(
    booking_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.core.exceptions import ForbiddenError
    from app.modules.audit.models import AuditLog
    from app.modules.bookings.models import Booking
    if current_user.role == "learner":
        booking_result = await db.execute(select(Booking).where(Booking.id == booking_id))
        booking = booking_result.scalar_one_or_none()
        if not booking or str(booking.learner_id) != str(current_user.id):
            raise ForbiddenError("Not your booking.")
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_type == "booking")
        .where(AuditLog.entity_id == str(booking_id))
        .order_by(AuditLog.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: uuid.UUID, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await BookingService(db).get(booking_id, caller_id=str(current_user.id), caller_role=current_user.role)


@router.patch("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await BookingService(db).confirm(booking_id, str(current_user.id))


@router.post("/{booking_id}/reschedule", response_model=BookingResponse)
async def reschedule_booking(
    booking_id: uuid.UUID,
    body: RescheduleRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BookingService(db).reschedule(booking_id, body, str(current_user.id), caller_role=current_user.role)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: uuid.UUID,
    body: CancelRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BookingService(db).cancel(booking_id, body, str(current_user.id), caller_role=current_user.role)
