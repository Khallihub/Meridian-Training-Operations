from __future__ import annotations

import csv
import hashlib
import hmac
import os
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.modules.bookings.models import Booking, BookingStatus
from app.modules.checkout.models import Order, OrderItem, OrderStatus
from app.modules.payments.models import (
    Payment, PaymentStatus, ReconciliationExport, Refund, RefundStatus,
)
from app.modules.payments.schemas import (
    PaymentCallbackPayload, PaymentResponse, ReconciliationExportResponse,
    RefundCreate, RefundResponse,
)


def _verify_signature(payload: PaymentCallbackPayload) -> bool:
    # order_id is bound into the message to prevent cross-order replay attacks
    message = f"{payload.order_id}{payload.terminal_ref}{payload.amount}{payload.timestamp}"
    expected = hmac.new(
        settings.PAYMENT_SIGNATURE_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, payload.signature)


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle_callback(self, payload: PaymentCallbackPayload) -> PaymentResponse:
        # --- Timestamp freshness (5-minute tolerance) ---
        try:
            cb_time = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))
            if abs((datetime.now(UTC) - cb_time).total_seconds()) > 300:
                raise UnprocessableError("Callback timestamp outside the 5-minute acceptance window.")
        except ValueError:
            raise UnprocessableError("Invalid timestamp format in callback.")

        # --- Durable idempotency: check external_event_id against the DB ---
        # This is the primary dedup mechanism (survives Redis restarts/eviction).
        if payload.external_event_id:
            dup_result = await self._db.execute(
                select(Payment).where(Payment.external_event_id == payload.external_event_id)
            )
            dup_payment = dup_result.scalar_one_or_none()
            if dup_payment:
                return PaymentResponse.model_validate(dup_payment)

        # --- Redis TTL dedup: secondary optimistic guard for callbacks without
        #     external_event_id (legacy / simulator) ---
        from app.core.security import get_redis
        cb_fp = hashlib.sha256(
            f"{payload.order_id}:{payload.terminal_ref}:{payload.timestamp}".encode()
        ).hexdigest()
        redis = get_redis()
        already_processed = await redis.get(f"cb_processed:{cb_fp}")

        sig_ok = _verify_signature(payload)

        # SELECT FOR UPDATE serialises concurrent callbacks for the same order.
        # Any second callback that arrives while the first is still processing
        # will block here until the first transaction commits, then read the
        # terminal state set by the first and short-circuit below.
        result = await self._db.execute(
            select(Payment)
            .where(Payment.order_id == payload.order_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment")

        # --- Short-circuit if already in terminal state ---
        if payment.status in (PaymentStatus.completed, PaymentStatus.failed):
            return PaymentResponse.model_validate(payment)

        # --- Short-circuit if this exact callback was already processed (Redis) ---
        if already_processed:
            return PaymentResponse.model_validate(payment)

        payment.terminal_ref = payload.terminal_ref
        payment.callback_received_at = datetime.now(UTC)
        payment.signature_verified = sig_ok
        payment.raw_callback = payload.model_dump(mode="json")
        # Persist the durable event key so future duplicate callbacks are rejected
        # at the DB level regardless of Redis state.
        if payload.external_event_id:
            payment.external_event_id = payload.external_event_id

        if sig_ok:
            # Verify payload amount matches stored payment amount before accepting
            if abs(float(payload.amount) - float(payment.amount)) > 0.001:
                payment.status = PaymentStatus.failed
                await self._db.flush()
                await log_audit(self._db, "system", "payment", str(payment.id), "callback_amount_mismatch",
                                new_value={"payload_amount": payload.amount, "expected": float(payment.amount)})
                return PaymentResponse.model_validate(payment)
            payment.status = PaymentStatus.completed
            await log_audit(self._db, "system", "payment", str(payment.id), "callback_completed",
                            new_value={"terminal_ref": payload.terminal_ref, "amount": payload.amount})
            # Mark order as paid
            order_result = await self._db.execute(select(Order).where(Order.id == payload.order_id))
            order = order_result.scalar_one_or_none()
            if order:
                order.status = OrderStatus.paid
                order.paid_at = datetime.now(UTC)
                # Auto-create pending bookings for each purchased session
                items_result = await self._db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id)
                )
                from app.modules.bookings.service import BookingService
                from app.modules.bookings.schemas import BookingCreate
                from app.core.exceptions import ConflictError as _ConflictError
                booking_svc = BookingService(self._db)
                booking_failures: list[str] = []
                for item in items_result.scalars().all():
                    try:
                        await booking_svc.create(
                            BookingCreate(session_id=item.session_id),
                            learner_id=order.learner_id,
                        )
                    except _ConflictError as exc:
                        # Session full or duplicate: record for compensation review
                        booking_failures.append(str(item.session_id))
                        await log_audit(
                            self._db, "system", "payment", str(payment.id),
                            "booking_conflict",
                            new_value={
                                "session_id": str(item.session_id),
                                "order_id": str(order.id),
                                "reason": str(exc),
                            },
                        )
                if booking_failures:
                    # Payment succeeded but some bookings failed — order needs refund, not closure
                    order.status = OrderStatus.refund_pending
                    await log_audit(
                        self._db, "system", "order", str(order.id),
                        "booking_conflict_needs_review",
                        new_value={"failed_sessions": booking_failures},
                    )
        else:
            payment.status = PaymentStatus.failed

        try:
            await self._db.flush()
        except IntegrityError:
            # The unique constraint on external_event_id fired — a concurrent
            # callback for the same event committed first.  Roll back the
            # in-flight changes and return the already-persisted payment state.
            await self._db.rollback()
            result2 = await self._db.execute(
                select(Payment).where(Payment.order_id == payload.order_id)
            )
            payment = result2.scalar_one_or_none()
            if not payment:
                raise NotFoundError("Payment")
            return PaymentResponse.model_validate(payment)

        # Persist idempotency key so duplicate callbacks are short-circuited (1-hour TTL)
        await redis.setex(f"cb_processed:{cb_fp}", 3600, "1")
        return PaymentResponse.model_validate(payment)

    async def simulate_payment(self, order_id: uuid.UUID) -> PaymentResponse:
        """Generate a valid signed callback internally — for the built-in terminal simulator."""
        import hashlib
        import hmac as hmac_mod

        order_result = await self._db.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order")

        terminal_ref = f"SIM-{str(order_id)[:8].upper()}"
        amount = float(order.total)
        timestamp = datetime.now(UTC).isoformat()
        message = f"{order_id}{terminal_ref}{amount}{timestamp}"
        signature = hmac_mod.new(
            settings.PAYMENT_SIGNATURE_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        from app.modules.payments.schemas import PaymentCallbackPayload
        payload = PaymentCallbackPayload(
            order_id=order_id,
            terminal_ref=terminal_ref,
            amount=amount,
            timestamp=timestamp,
            signature=signature,
        )
        return await self.handle_callback(payload)

    async def list_payments(self, page: int = 1, page_size: int = 50) -> tuple[list[PaymentResponse], int]:
        from sqlalchemy import func
        count_result = await self._db.execute(select(func.count()).select_from(Payment))
        total = count_result.scalar_one()
        offset = (page - 1) * page_size
        result = await self._db.execute(
            select(Payment).order_by(Payment.created_at.desc()).offset(offset).limit(page_size)
        )
        items = [PaymentResponse.model_validate(p) for p in result.scalars().all()]
        return items, total

    async def get_payment(self, order_id: uuid.UUID) -> PaymentResponse:
        result = await self._db.execute(select(Payment).where(Payment.order_id == order_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment")
        return PaymentResponse.model_validate(payment)

    async def create_refund(self, payload: RefundCreate, requester_id: uuid.UUID) -> RefundResponse:
        payment_result = await self._db.execute(
            select(Payment).where(Payment.order_id == payload.order_id, Payment.status == PaymentStatus.completed)
        )
        payment = payment_result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment for order")
        if float(payload.amount) > float(payment.amount):
            raise UnprocessableError("Refund amount exceeds payment amount.")

        refund = Refund(
            payment_id=payment.id,
            requested_by=requester_id,
            amount=payload.amount,
            reason=payload.reason,
            status=RefundStatus.requested,
        )
        self._db.add(refund)
        await self._db.flush()
        await log_audit(self._db, str(requester_id), "refund", str(refund.id), "create")
        return RefundResponse.model_validate(refund)

    async def list_refunds(self, status: str | None = None) -> list[RefundResponse]:
        q = select(Refund)
        if status:
            q = q.where(Refund.status == status)
        result = await self._db.execute(q.order_by(Refund.created_at.desc()))
        return [RefundResponse.model_validate(r) for r in result.scalars().all()]

    async def get_export(self, export_id: uuid.UUID) -> ReconciliationExport:
        result = await self._db.execute(select(ReconciliationExport).where(ReconciliationExport.id == export_id))
        export = result.scalar_one_or_none()
        if not export:
            raise NotFoundError("Export")
        return export

    async def get_refund(self, refund_id: uuid.UUID) -> RefundResponse:
        result = await self._db.execute(select(Refund).where(Refund.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundError("Refund")
        return RefundResponse.model_validate(r)

    async def review_refund(self, refund_id: uuid.UUID, actor_id: str) -> RefundResponse:
        """Move refund from requested → pending_review (finance acknowledges and begins review)."""
        result = await self._db.execute(select(Refund).where(Refund.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundError("Refund")
        if r.status != RefundStatus.requested:
            raise ConflictError(f"Refund must be in 'requested' state to begin review; current state: {r.status}.")
        r.status = RefundStatus.pending_review
        await self._db.flush()
        await log_audit(self._db, actor_id, "refund", str(refund_id), "review")
        return RefundResponse.model_validate(r)

    async def approve_refund(self, refund_id: uuid.UUID, actor_id: str) -> RefundResponse:
        """Move refund from pending_review → approved."""
        result = await self._db.execute(select(Refund).where(Refund.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundError("Refund")
        if r.status != RefundStatus.pending_review:
            raise ConflictError(f"Refund must be in 'pending_review' state to approve; current state: {r.status}.")
        r.status = RefundStatus.approved
        await self._db.flush()
        await log_audit(self._db, actor_id, "refund", str(refund_id), "approve")
        return RefundResponse.model_validate(r)

    async def reject_refund(self, refund_id: uuid.UUID, actor_id: str) -> RefundResponse:
        """Move refund from pending_review → rejected (terminal)."""
        result = await self._db.execute(select(Refund).where(Refund.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundError("Refund")
        if r.status != RefundStatus.pending_review:
            raise ConflictError(f"Refund must be in 'pending_review' state to reject; current state: {r.status}.")
        r.status = RefundStatus.rejected
        r.processed_at = datetime.now(UTC)
        await self._db.flush()
        await log_audit(self._db, actor_id, "refund", str(refund_id), "reject")
        return RefundResponse.model_validate(r)

    async def process_refund(self, refund_id: uuid.UUID, actor_id: str) -> RefundResponse:
        """Move refund from approved → processing (payment is being issued)."""
        result = await self._db.execute(select(Refund).where(Refund.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundError("Refund")
        if r.status != RefundStatus.approved:
            raise ConflictError(f"Refund must be 'approved' before processing; current state: {r.status}.")
        r.status = RefundStatus.processing
        await self._db.flush()
        await log_audit(self._db, actor_id, "refund", str(refund_id), "process")
        return RefundResponse.model_validate(r)

    async def complete_refund(self, refund_id: uuid.UUID, actor_id: str) -> RefundResponse:
        """Move refund from processing → completed."""
        result = await self._db.execute(select(Refund).where(Refund.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundError("Refund")
        if r.status != RefundStatus.processing:
            raise ConflictError(f"Refund must be in 'processing' state to complete; current state: {r.status}.")
        r.status = RefundStatus.completed
        r.processed_at = datetime.now(UTC)

        # Determine full vs partial refund and update order status accordingly
        payment_result = await self._db.execute(select(Payment).where(Payment.id == r.payment_id))
        payment = payment_result.scalar_one_or_none()
        if payment:
            from sqlalchemy import func as _func
            prior_completed = await self._db.execute(
                select(_func.coalesce(_func.sum(Refund.amount), 0))
                .where(Refund.payment_id == payment.id, Refund.status == RefundStatus.completed, Refund.id != r.id)
            )
            prior_amount = float(prior_completed.scalar_one() or 0)
            total_refunded = prior_amount + float(r.amount)

            order_result = await self._db.execute(select(Order).where(Order.id == payment.order_id))
            order = order_result.scalar_one_or_none()
            if order:
                if total_refunded >= float(payment.amount):
                    order.status = OrderStatus.refunded_full
                else:
                    order.status = OrderStatus.refunded_partial

        await self._db.flush()
        await log_audit(self._db, actor_id, "refund", str(refund_id), "complete")
        return RefundResponse.model_validate(r)

    async def generate_reconciliation_export(self, export_date: date | None = None) -> ReconciliationExportResponse:
        """Generate daily reconciliation CSV. Used by Celery and by the API endpoint."""
        from datetime import timezone

        if not export_date:
            export_date = (datetime.now(UTC) - timedelta(days=1)).date()

        day_start = datetime(export_date.year, export_date.month, export_date.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        result = await self._db.execute(
            select(Payment, Order)
            .join(Order, Payment.order_id == Order.id)
            .where(
                and_(
                    Payment.status == PaymentStatus.completed,
                    Payment.callback_received_at >= day_start,
                    Payment.callback_received_at < day_end,
                )
            )
        )
        rows = result.all()

        os.makedirs(settings.EXPORTS_DIR, exist_ok=True)
        filepath = os.path.join(settings.EXPORTS_DIR, f"reconciliation_{export_date}.csv")

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["payment_id", "order_id", "learner_id", "amount", "currency", "terminal_ref", "paid_at"])
            for payment, order in rows:
                writer.writerow([
                    str(payment.id), str(order.id), str(order.learner_id),
                    float(payment.amount), order.currency,
                    payment.terminal_ref or "",
                    order.paid_at.isoformat() if order.paid_at else "",
                ])

        rec = ReconciliationExport(
            export_date=day_start,
            file_path=filepath,
            row_count=len(rows),
        )
        self._db.add(rec)
        await self._db.flush()
        return ReconciliationExportResponse.model_validate(rec)

    async def list_exports(self) -> list[ReconciliationExportResponse]:
        result = await self._db.execute(
            select(ReconciliationExport).order_by(ReconciliationExport.export_date.desc()).limit(90)
        )
        return [ReconciliationExportResponse.model_validate(r) for r in result.scalars().all()]
