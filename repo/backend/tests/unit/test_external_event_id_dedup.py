"""Unit tests for durable external_event_id duplicate-callback replay protection.

These tests exercise PaymentService.handle_callback() using an in-memory mock
of the database session so they run without a real PostgreSQL instance.  They
prove the three dedup scenarios required by the PRD:

1. A callback whose external_event_id already exists in the DB is rejected
   (returns existing payment, no write).
2. A callback without external_event_id falls through to the Redis TTL guard.
3. A concurrent INSERT that loses the race (IntegrityError on flush) is caught
   and returns the already-committed payment state.
"""
from __future__ import annotations

import hashlib
import hmac
import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.schemas import PaymentCallbackPayload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(
    order_id: uuid.UUID | None = None,
    external_event_id: str | None = "evt-001",
    amount: float = 100.0,
    sig: str | None = None,
) -> PaymentCallbackPayload:
    oid = order_id or uuid.uuid4()
    terminal_ref = "TERM-001"
    ts = datetime.now(UTC).isoformat()
    if sig is None:
        # Build a valid HMAC so signature verification passes
        from app.core.config import settings
        message = f"{oid}{terminal_ref}{amount}{ts}"
        sig = hmac.new(
            settings.PAYMENT_SIGNATURE_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
    return PaymentCallbackPayload(
        order_id=oid,
        terminal_ref=terminal_ref,
        amount=amount,
        timestamp=ts,
        signature=sig,
        external_event_id=external_event_id,
    )


def _make_payment(
    order_id: uuid.UUID,
    status: PaymentStatus = PaymentStatus.pending,
    amount: float = 100.0,
    external_event_id: str | None = None,
) -> Payment:
    p = Payment()
    p.id = uuid.uuid4()
    p.order_id = order_id
    p.status = status
    p.amount = amount
    p.external_event_id = external_event_id
    p.terminal_ref = None
    p.callback_received_at = None
    p.signature_verified = False
    p.raw_callback = None
    p.created_at = datetime.now(UTC)
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDurableExternalEventIdDedup:
    """Primary dedup path: DB unique constraint on external_event_id."""

    @pytest.mark.asyncio
    async def test_duplicate_external_event_id_returns_existing_payment(self):
        """If a Payment row already carries the same external_event_id, the
        callback is short-circuited before any state mutation."""
        from app.modules.payments.service import PaymentService

        order_id = uuid.uuid4()
        existing_payment = _make_payment(
            order_id, PaymentStatus.completed, external_event_id="evt-001"
        )
        payload = _make_payload(order_id=order_id, external_event_id="evt-001")

        db = AsyncMock()
        # First execute call (dedup SELECT) returns the existing completed payment.
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = existing_payment
        db.execute = AsyncMock(return_value=dup_result)

        with patch("app.core.security.get_redis") as mock_redis_factory:
            mock_redis_factory.return_value = AsyncMock()
            svc = PaymentService(db)
            response = await svc.handle_callback(payload)

        # Should return the existing payment without any additional DB writes.
        assert str(response.id) == str(existing_payment.id)
        assert response.status == PaymentStatus.completed
        # flush must NOT have been called (no mutation)
        db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_external_event_id_proceeds_to_processing(self):
        """A callback with a novel external_event_id reaches the write path."""
        from app.modules.payments.service import PaymentService

        order_id = uuid.uuid4()
        pending_payment = _make_payment(order_id, PaymentStatus.pending)
        payload = _make_payload(order_id=order_id, external_event_id="evt-new")

        db = AsyncMock()
        call_count = 0

        async def execute_side_effect(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Dedup SELECT — no existing payment with this event ID
                result.scalar_one_or_none.return_value = None
            elif call_count == 2:
                # SELECT FOR UPDATE — the payment row
                result.scalar_one_or_none.return_value = pending_payment
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        with patch("app.core.security.get_redis") as mock_redis_factory:
            redis_mock = AsyncMock()
            redis_mock.get = AsyncMock(return_value=None)
            redis_mock.setex = AsyncMock()
            mock_redis_factory.return_value = redis_mock
            with patch("app.modules.payments.service.log_audit", new_callable=AsyncMock):
                with patch("app.modules.payments.service.PaymentService._db", db, create=True):
                    svc = PaymentService(db)
                    # Patch the inner booking service call to avoid deep mocking
                    with patch("app.modules.bookings.service.BookingService") as _bs:
                        await svc.handle_callback(payload)

        # external_event_id must be stamped onto the payment row
        assert pending_payment.external_event_id == "evt-new"

    @pytest.mark.asyncio
    async def test_callback_without_external_event_id_skips_db_dedup(self):
        """Callbacks omitting external_event_id skip the DB dedup SELECT entirely
        and rely on the Redis fallback guard."""
        from app.modules.payments.service import PaymentService

        order_id = uuid.uuid4()
        pending_payment = _make_payment(order_id, PaymentStatus.pending)
        # No external_event_id; use an invalid signature so the service takes the
        # short sig_ok=False path — this test is only about the dedup SELECT skip.
        payload = _make_payload(order_id=order_id, external_event_id=None, sig="invalid-sig")

        db = AsyncMock()
        call_count = 0

        async def execute_side_effect(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            # First call should be the SELECT FOR UPDATE (no dedup SELECT)
            result.scalar_one_or_none.return_value = pending_payment
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        with patch("app.core.security.get_redis") as mock_redis_factory:
            redis_mock = AsyncMock()
            redis_mock.get = AsyncMock(return_value=None)
            redis_mock.setex = AsyncMock()
            mock_redis_factory.return_value = redis_mock
            with patch("app.modules.payments.service.log_audit", new_callable=AsyncMock):
                svc = PaymentService(db)
                with patch("app.modules.bookings.service.BookingService"):
                    await svc.handle_callback(payload)

        # Only 1 DB execute call (the FOR UPDATE) — the dedup SELECT was skipped
        assert call_count == 1
        # external_event_id was not set (payload had none)
        assert pending_payment.external_event_id is None


class TestIntegrityErrorRaceHandling:
    """IntegrityError on flush means a concurrent callback won the race.
    The service must roll back and re-read the committed state."""

    @pytest.mark.asyncio
    async def test_integrity_error_on_flush_returns_committed_payment(self):
        """When flush() raises IntegrityError (unique constraint violation on
        external_event_id), the service rolls back, re-fetches the payment,
        and returns the already-committed state without re-raising."""
        from sqlalchemy.exc import IntegrityError as _IntegrityError
        from app.modules.payments.service import PaymentService

        order_id = uuid.uuid4()
        pending_payment = _make_payment(order_id, PaymentStatus.pending)
        committed_payment = _make_payment(order_id, PaymentStatus.completed, external_event_id="evt-race")
        # Invalid signature keeps the service on the sig_ok=False path so that
        # the execute mock (3 calls: dedup SELECT, FOR UPDATE, re-fetch) is
        # exhaustive and flush() raises the IntegrityError we're testing.
        payload = _make_payload(order_id=order_id, external_event_id="evt-race", sig="invalid-sig")

        db = AsyncMock()
        call_count = 0

        async def execute_side_effect(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Dedup SELECT — not found yet (race hasn't committed yet)
                result.scalar_one_or_none.return_value = None
            elif call_count == 2:
                # SELECT FOR UPDATE
                result.scalar_one_or_none.return_value = pending_payment
            elif call_count == 3:
                # Re-fetch after rollback
                result.scalar_one_or_none.return_value = committed_payment
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)
        db.flush = AsyncMock(side_effect=_IntegrityError("unique violation", {}, None))
        db.rollback = AsyncMock()

        with patch("app.core.security.get_redis") as mock_redis_factory:
            redis_mock = AsyncMock()
            redis_mock.get = AsyncMock(return_value=None)
            redis_mock.setex = AsyncMock()
            mock_redis_factory.return_value = redis_mock
            with patch("app.modules.payments.service.log_audit", new_callable=AsyncMock):
                svc = PaymentService(db)
                response = await svc.handle_callback(payload)

        # Must return the already-committed payment, not raise
        assert str(response.id) == str(committed_payment.id)
        assert response.status == PaymentStatus.completed
        db.rollback.assert_called_once()
