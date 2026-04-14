from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.checkout.best_offer import compute_best_offer
from app.modules.checkout.models import Order, OrderItem, OrderPromotion, OrderStatus
from app.modules.checkout.schemas import (
    AppliedPromotionDetail, BestOfferResponse, CartCreate, OrderResponse,
)
from app.modules.courses.models import Course
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.promotions.models import Promotion
from app.modules.sessions.models import Session, SessionStatus

# States in which a session may be purchased/booked
_BOOKABLE_STATUSES = {SessionStatus.scheduled}


class CheckoutService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _get_session_price(self, session_id: uuid.UUID) -> tuple[float, str]:
        """Returns (price, course_id_str)."""
        result = await self._db.execute(
            select(Session, Course).join(Course, Session.course_id == Course.id).where(Session.id == session_id)
        )
        row = result.first()
        if not row:
            raise NotFoundError("Session")
        session, course = row
        if session.status not in _BOOKABLE_STATUSES:
            raise ConflictError(f"Session is not available for purchase (status: {session.status}).")
        return float(course.price), str(course.id)

    async def create_cart(self, payload: CartCreate, learner_id: uuid.UUID) -> OrderResponse:
        subtotal = 0.0
        items_data: list[dict] = []

        for item in payload.items:
            price, course_id = await self._get_session_price(item.session_id)
            line_total = price * item.quantity
            subtotal += line_total
            items_data.append({"session_id": item.session_id, "unit_price": price, "quantity": item.quantity, "course_id": course_id})

        # Compute best-offer automatically
        course_ids = {i["course_id"] for i in items_data}
        # Expand to individual unit prices for BOGO quantity-aware calculation
        item_prices = [i["unit_price"] for i in items_data for _ in range(i["quantity"])]
        promos_result = await self._db.execute(
            select(Promotion)
            .where(Promotion.is_active == True)
            .order_by(Promotion.priority.asc(), Promotion.id.asc())
        )
        all_promos = promos_result.scalars().all()
        applied = compute_best_offer(list(all_promos), subtotal, course_ids, item_prices)

        discount_total = sum(a.discount_amount for a in applied)
        total = max(0.0, subtotal - discount_total)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.ORDER_EXPIRY_MINUTES)

        order = Order(
            learner_id=learner_id,
            status=OrderStatus.awaiting_payment,
            subtotal=round(subtotal, 2),
            discount_total=round(discount_total, 2),
            total=round(total, 2),
            expires_at=expires_at,
        )
        self._db.add(order)
        await self._db.flush()

        for item in items_data:
            oi = OrderItem(order_id=order.id, session_id=item["session_id"], unit_price=item["unit_price"], quantity=item["quantity"])
            self._db.add(oi)

        for a in applied:
            op = OrderPromotion(
                order_id=order.id,
                promotion_id=a.promotion.id,
                discount_amount=a.discount_amount,
                explanation=a.explanation,
            )
            self._db.add(op)

        payment = Payment(order_id=order.id, amount=order.total, status=PaymentStatus.pending)
        self._db.add(payment)

        await self._db.flush()
        await self._db.refresh(order)

        return await self.get_order(order.id)

    async def get_best_offer(self, payload: CartCreate) -> BestOfferResponse:
        """Dry-run best-offer calculation without persisting."""
        subtotal = 0.0
        course_ids: set[str] = set()
        item_prices_preview: list[float] = []

        for item in payload.items:
            price, course_id = await self._get_session_price(item.session_id)
            line_total = price * item.quantity
            subtotal += line_total
            course_ids.add(course_id)
            item_prices_preview.extend([price] * item.quantity)

        promos_result = await self._db.execute(
            select(Promotion)
            .where(Promotion.is_active == True)
            .order_by(Promotion.priority.asc(), Promotion.id.asc())
        )
        all_promos = promos_result.scalars().all()
        applied = compute_best_offer(list(all_promos), subtotal, course_ids, item_prices_preview)
        discount_total = sum(a.discount_amount for a in applied)

        return BestOfferResponse(
            subtotal=round(subtotal, 2),
            discount_total=round(discount_total, 2),
            total=round(max(0.0, subtotal - discount_total), 2),
            applied_promotions=[
                AppliedPromotionDetail(
                    promotion_id=a.promotion.id,
                    promotion_name=a.promotion.name,
                    discount_amount=a.discount_amount,
                    explanation=a.explanation,
                )
                for a in applied
            ],
        )

    async def get_order(self, order_id: uuid.UUID, caller_id: str | None = None, caller_role: str | None = None) -> OrderResponse:
        from sqlalchemy.orm import selectinload
        result = await self._db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.applied_promotions))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order")
        if caller_role not in ("admin", "finance") and caller_id and str(order.learner_id) != caller_id:
            raise ForbiddenError("Not your order")

        # Fetch session titles for all items in one query
        session_ids = [i.session_id for i in order.items]
        titles: dict[uuid.UUID, str] = {}
        if session_ids:
            sess_result = await self._db.execute(
                select(Session).where(Session.id.in_(session_ids))
            )
            for s in sess_result.scalars().all():
                titles[s.id] = s.title

        # Build response manually to include promotion details
        items_resp = [
            {"id": i.id, "session_id": i.session_id, "session_title": titles.get(i.session_id), "unit_price": float(i.unit_price), "quantity": i.quantity}
            for i in order.items
        ]

        promo_details = []
        for op in order.applied_promotions:
            promo_result = await self._db.execute(select(Promotion).where(Promotion.id == op.promotion_id))
            promo = promo_result.scalar_one_or_none()
            promo_details.append(AppliedPromotionDetail(
                promotion_id=op.promotion_id,
                promotion_name=promo.name if promo else "Unknown",
                discount_amount=float(op.discount_amount),
                explanation=op.explanation or "",
            ))

        from app.modules.checkout.schemas import OrderItemResponse
        return OrderResponse(
            id=order.id,
            learner_id=order.learner_id,
            status=order.status,
            subtotal=float(order.subtotal),
            discount_total=float(order.discount_total),
            total=float(order.total),
            currency=order.currency,
            created_at=order.created_at,
            paid_at=order.paid_at,
            expires_at=order.expires_at,
            items=[OrderItemResponse(**i) for i in items_resp],
            applied_promotions=promo_details,
        )

    async def cancel_order(self, order_id: uuid.UUID, caller_id: str | None = None, caller_role: str | None = None) -> OrderResponse:
        result = await self._db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order")
        if caller_role not in ("admin", "finance") and caller_id and str(order.learner_id) != caller_id:
            raise ForbiddenError("Not your order")
        if order.status == OrderStatus.paid:
            raise ConflictError("Cannot cancel a paid order; submit a refund instead.")
        order.status = OrderStatus.canceled
        order.closed_at = datetime.now(UTC)
        await self._db.flush()
        return await self.get_order(order_id)

    async def list_orders(
        self, learner_id: uuid.UUID | None, page: int, page_size: int
    ) -> tuple[list[OrderResponse], int]:
        from sqlalchemy import func
        q = select(Order)
        if learner_id:
            q = q.where(Order.learner_id == learner_id)
        count_result = await self._db.execute(select(func.count()).select_from(q.subquery()))
        total = count_result.scalar_one()
        offset = (page - 1) * page_size
        result = await self._db.execute(q.order_by(Order.created_at.desc()).offset(offset).limit(page_size))
        orders = result.scalars().all()
        items = []
        for o in orders:
            items.append(await self.get_order(o.id))
        return items, total
