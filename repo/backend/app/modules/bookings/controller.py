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
    if current_user.role in ("admin", "instructor"):
        learner_id = None
    elif current_user.role == "finance":
        # Finance must scope to a specific session; row-level payment filtering is
        # enforced in the repository via finance_payment_scoped flag below.
        if not session_id:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Finance must provide session_id to list bookings.")
        learner_id = None
    else:
        learner_id = current_user.id
    # Instructors only see bookings for sessions they own.
    # session.instructor_id references instructors.id, not users.id — must look up
    # the Instructor record to get the correct entity ID for the filter.
    instructor_id = None
    if current_user.role == "instructor":
        from sqlalchemy import select as _sel
        from app.modules.instructors.models import Instructor as _Instructor
        _instr_result = await db.execute(
            _sel(_Instructor).where(_Instructor.user_id == current_user.id)
        )
        _instr = _instr_result.scalar_one_or_none()
        # Use a zero UUID if no instructor record exists so the query returns nothing
        # rather than bypassing the filter entirely.
        instructor_id = _instr.id if _instr else uuid.UUID(int=0)
    items, total = await BookingService(db).list(
        learner_id, session_id, status, page, page_size,
        instructor_id=instructor_id,
        finance_payment_scoped=(current_user.role == "finance"),
    )
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
    from app.modules.sessions.models import Session
    if current_user.role != "admin":
        booking_result = await db.execute(select(Booking).where(Booking.id == booking_id))
        booking = booking_result.scalar_one_or_none()
        if current_user.role == "learner":
            if not booking or str(booking.learner_id) != str(current_user.id):
                raise ForbiddenError("Not your booking.")
        elif current_user.role == "instructor":
            if not booking:
                raise ForbiddenError("Not your booking.")
            session_result = await db.execute(select(Session).where(Session.id == booking.session_id))
            session = session_result.scalar_one_or_none()
            # session.instructor_id is instructors.id, not users.id — resolve via Instructor record.
            from app.modules.instructors.models import Instructor
            instr_result = await db.execute(
                select(Instructor).where(Instructor.user_id == current_user.id)
            )
            instructor = instr_result.scalar_one_or_none()
            if not session or not instructor or session.instructor_id != instructor.id:
                raise ForbiddenError("Not your booking.")
        elif current_user.role == "finance":
            if not booking:
                raise ForbiddenError("Not your booking.")
            from sqlalchemy import exists as _exists, and_ as _and_
            from app.modules.checkout.models import Order, OrderItem
            assoc_result = await db.execute(
                select(_exists().where(
                    _and_(
                        OrderItem.session_id == booking.session_id,
                        Order.learner_id == booking.learner_id,
                        OrderItem.order_id == Order.id,
                    )
                ))
            )
            if not assoc_result.scalar():
                raise ForbiddenError("Not your booking.")
        else:
            # dataops and any other non-admin role has no booking history access.
            raise ForbiddenError("Access denied.")
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
    return await BookingService(db).confirm(booking_id, str(current_user.id), caller_role=current_user.role)


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
