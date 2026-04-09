from __future__ import annotations

import csv
import io
import time
import uuid
from datetime import UTC

from sqlalchemy import and_, distinct, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_field
from app.core.exceptions import AppError, NotFoundError
from app.core.masking import mask_phone
from app.modules.bookings.models import Booking, BookingStatus
from app.modules.checkout.models import Order, OrderItem
from app.modules.courses.models import Course
from app.modules.instructors.models import Instructor
from app.modules.locations.models import Location, Room
from app.modules.search.models import SavedSearch
from app.modules.search.schemas import (
    ExportRequest, FacetCount, SavedSearchCreate, SavedSearchResponse,
    SearchFacets, SearchFilters, SearchResponse, SearchResultItem,
)
from app.modules.sessions.models import Session
from app.modules.users.models import User


def _build_count_query(filters: SearchFilters):
    """Simplified count query — same joins/filters as _build_base_query but no scalar subquery columns."""
    q = (
        select(func.count(Booking.id))
        .join(User, Booking.learner_id == User.id)
        .join(Session, Booking.session_id == Session.id)
        .join(Course, Session.course_id == Course.id)
        .join(Room, Session.room_id == Room.id)
        .join(Location, Room.location_id == Location.id)
        .join(Instructor, Session.instructor_id == Instructor.id)
    )
    if filters.enrollment_status:
        q = q.where(Booking.status == filters.enrollment_status)
    if filters.learner_id:
        q = q.where(Booking.learner_id == filters.learner_id)
    if filters.site_id:
        q = q.where(Location.id == filters.site_id)
    if filters.instructor_id:
        q = q.where(Instructor.id == filters.instructor_id)
    if filters.date_range:
        if filters.date_range.from_:
            q = q.where(Session.start_time >= filters.date_range.from_)
        if filters.date_range.to:
            q = q.where(Session.start_time <= filters.date_range.to)
    if filters.date_from:
        q = q.where(Session.start_time >= filters.date_from)
    if filters.date_to:
        q = q.where(Session.start_time <= filters.date_to)
    if filters.invoice_number:
        q = q.where(
            select(Order.id)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(OrderItem.session_id == Booking.session_id)
            .where(Order.learner_id == Booking.learner_id)
            .where(text("CAST(orders.id AS text) ILIKE :inv").bindparams(inv=f"%{filters.invoice_number}%"))
            .exists()
        )
    return q


def _build_base_query(filters: SearchFilters):
    """Build a SQLAlchemy select against bookings joined to all related tables."""
    q = (
        select(
            Booking.id.label("booking_id"),
            Booking.session_id,
            Booking.learner_id,
            Booking.status.label("status"),
            User.username.label("learner_username"),
            User.phone_encrypted.label("phone_encrypted"),
            Session.start_time.label("session_date"),
            Course.title.label("session_title"),
            Location.name.label("site_name"),
            Location.id.label("site_id"),
            Instructor.id.label("instructor_id"),
            select(User.username)
            .where(User.id == Instructor.user_id)
            .correlate(Instructor)
            .scalar_subquery()
            .label("instructor_name"),
            select(Order.id)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(OrderItem.session_id == Booking.session_id)
            .where(Order.learner_id == Booking.learner_id)
            .limit(1)
            .correlate(Booking)
            .scalar_subquery()
            .label("order_id"),
            select(Order.total)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(OrderItem.session_id == Booking.session_id)
            .where(Order.learner_id == Booking.learner_id)
            .where(Order.status == "paid")
            .limit(1)
            .correlate(Booking)
            .scalar_subquery()
            .label("amount"),
        )
        .join(User, Booking.learner_id == User.id)
        .join(Session, Booking.session_id == Session.id)
        .join(Course, Session.course_id == Course.id)
        .join(Room, Session.room_id == Room.id)
        .join(Location, Room.location_id == Location.id)
        .join(Instructor, Session.instructor_id == Instructor.id)
    )

    if filters.enrollment_status:
        q = q.where(Booking.status == filters.enrollment_status)
    if filters.learner_id:
        q = q.where(Booking.learner_id == filters.learner_id)
    if filters.site_id:
        q = q.where(Location.id == filters.site_id)
    if filters.instructor_id:
        q = q.where(Instructor.id == filters.instructor_id)
    if filters.date_range:
        if filters.date_range.from_:
            q = q.where(Session.start_time >= filters.date_range.from_)
        if filters.date_range.to:
            q = q.where(Session.start_time <= filters.date_range.to)
    if filters.date_from:
        q = q.where(Session.start_time >= filters.date_from)
    if filters.date_to:
        q = q.where(Session.start_time <= filters.date_to)
    if filters.invoice_number:
        # pg_trgm similarity on order UUID text
        q = q.where(
            select(Order.id)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(OrderItem.session_id == Booking.session_id)
            .where(Order.learner_id == Booking.learner_id)
            .where(text("CAST(orders.id AS text) ILIKE :inv").bindparams(inv=f"%{filters.invoice_number}%"))
            .exists()
        )

    return q


class SearchService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search(self, filters: SearchFilters) -> SearchResponse:
        t0 = time.monotonic()
        q = _build_base_query(filters)
        page_size = min(filters.page_size, settings.MAX_PAGE_SIZE)

        # Phone filter requires decrypt-then-match in Python.
        # When active, we fetch all matching rows first so the post-filter count is accurate.
        phone_filter = filters.learner_phone

        if phone_filter:
            # Fetch all candidate rows (no SQL-level phone filter), then filter + paginate in Python
            all_result = await self._db.execute(q.order_by(text("bookings.created_at DESC")))
            all_rows = all_result.mappings().all()

            filtered: list = []
            for row in all_rows:
                phone_raw = decrypt_field(row["phone_encrypted"]) if row.get("phone_encrypted") else None
                if phone_filter not in (phone_raw or ""):
                    continue
                filtered.append((row, phone_raw))

            total = len(filtered)
            offset = (filters.page - 1) * page_size
            page_rows = filtered[offset: offset + page_size]

            items: list[SearchResultItem] = []
            for row, phone_raw in page_rows:
                items.append(SearchResultItem(
                    booking_id=row["booking_id"],
                    session_id=row["session_id"],
                    learner_id=row["learner_id"],
                    learner_username=row["learner_username"],
                    learner_phone_masked=mask_phone(phone_raw),
                    status=row["status"],
                    session_date=row["session_date"],
                    session_title=row["session_title"],
                    instructor_name=row.get("instructor_name") or "",
                    site_name=row["site_name"],
                    order_id=row.get("order_id"),
                    amount=float(row["amount"]) if row.get("amount") is not None else None,
                ))
        else:
            # No phone filter: use SQL count and SQL-level pagination for efficiency
            count_result = await self._db.execute(_build_count_query(filters))
            total = count_result.scalar_one()

            offset = (filters.page - 1) * page_size
            result = await self._db.execute(q.order_by(text("bookings.created_at DESC")).offset(offset).limit(page_size))
            rows = result.mappings().all()

            items = []
            for row in rows:
                phone_raw = decrypt_field(row["phone_encrypted"]) if row.get("phone_encrypted") else None
                items.append(SearchResultItem(
                    booking_id=row["booking_id"],
                    session_id=row["session_id"],
                    learner_id=row["learner_id"],
                    learner_username=row["learner_username"],
                    learner_phone_masked=mask_phone(phone_raw),
                    status=row["status"],
                    session_date=row["session_date"],
                    session_title=row["session_title"],
                    instructor_name=row.get("instructor_name") or "",
                    site_name=row["site_name"],
                    order_id=row.get("order_id"),
                    amount=float(row["amount"]) if row.get("amount") is not None else None,
                ))

        elapsed = (time.monotonic() - t0) * 1000

        # Facets
        facets = None
        if filters.include_facets:
            facets = await self._compute_facets(filters)

        return SearchResponse(
            results=items,
            total_count=total,
            page=filters.page,
            page_size=page_size,
            has_next=(filters.page * page_size < total),
            query_time_ms=round(elapsed, 1),
            facets=facets,
        )

    async def _compute_facets(self, filters: SearchFilters) -> SearchFacets:
        base = _build_base_query(SearchFilters(
            # Facets ignore pagination + enrollment_status to show all counts
            site_id=filters.site_id,
            instructor_id=filters.instructor_id,
            date_range=filters.date_range,
        ))
        base_sub = base.subquery()

        # Enrollment status facet
        status_result = await self._db.execute(
            select(base_sub.c.status, func.count().label("cnt"))
            .group_by(base_sub.c.status)
        )
        status_facet = {row.status: row.cnt for row in status_result.all()}

        # Site facet
        site_result = await self._db.execute(
            select(base_sub.c.site_id, base_sub.c.site_name, func.count().label("cnt"))
            .group_by(base_sub.c.site_id, base_sub.c.site_name)
        )
        site_facet = [FacetCount(id=str(r.site_id), name=r.site_name, count=r.cnt) for r in site_result.all()]

        # Instructor facet
        instr_result = await self._db.execute(
            select(base_sub.c.instructor_id, base_sub.c.instructor_name, func.count().label("cnt"))
            .group_by(base_sub.c.instructor_id, base_sub.c.instructor_name)
        )
        instr_facet = [FacetCount(id=str(r.instructor_id), name=r.instructor_name or "", count=r.cnt) for r in instr_result.all()]

        return SearchFacets(enrollment_status=status_facet, site=site_facet, instructor=instr_facet)

    async def export(self, filters: SearchFilters, fmt: str) -> bytes:
        if filters.page_size > settings.EXPORT_ROW_LIMIT:
            filters.page_size = settings.EXPORT_ROW_LIMIT
        filters.page = 1

        # Check total first
        q = _build_base_query(filters)
        count_result = await self._db.execute(_build_count_query(filters))
        total = count_result.scalar_one()
        if total > settings.EXPORT_ROW_LIMIT:
            raise AppError(f"Export exceeds {settings.EXPORT_ROW_LIMIT} rows. Apply narrower filters.", 400)

        result = await self._db.execute(q.order_by(text("bookings.created_at DESC")).limit(settings.EXPORT_ROW_LIMIT))
        rows = result.mappings().all()

        # Keys must match the column aliases produced by _build_base_query
        headers = ["booking_id", "session_id", "learner_id", "learner_username", "status",
                   "session_date", "session_title", "instructor_name", "site_name", "order_id"]

        if fmt == "excel":
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(headers)
            for row in rows:
                ws.append([str(row.get(h) or "") for h in headers])
            buf = io.BytesIO()
            wb.save(buf)
            return buf.getvalue()
        else:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(row.get(h) or "") for h in headers])
            return buf.getvalue().encode()

    async def save_search(self, user_id: uuid.UUID, payload: SavedSearchCreate) -> SavedSearchResponse:
        from sqlalchemy import func as sqlfunc
        count_result = await self._db.execute(
            select(func.count()).where(SavedSearch.user_id == user_id)
        )
        count = count_result.scalar_one()
        if count >= 20:
            raise AppError("Maximum of 20 saved searches per user reached.", 400)

        ss = SavedSearch(user_id=user_id, name=payload.name, filters_json=payload.filters)
        self._db.add(ss)
        await self._db.flush()
        return SavedSearchResponse.model_validate(ss)

    async def list_saved_searches(self, user_id: uuid.UUID) -> list[SavedSearchResponse]:
        result = await self._db.execute(
            select(SavedSearch).where(SavedSearch.user_id == user_id).order_by(SavedSearch.created_at.desc())
        )
        return [SavedSearchResponse.model_validate(s) for s in result.scalars().all()]

    async def delete_saved_search(self, search_id: uuid.UUID, user_id: uuid.UUID) -> None:
        result = await self._db.execute(
            select(SavedSearch).where(and_(SavedSearch.id == search_id, SavedSearch.user_id == user_id))
        )
        ss = result.scalar_one_or_none()
        if not ss:
            raise NotFoundError("Saved search")
        await self._db.delete(ss)
        await self._db.flush()
