"""API tests for payment callback and refund flow."""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import make_user, resp_data
from app.modules.users.models import UserRole


@pytest.mark.asyncio
class TestPaymentCallback:
    async def test_valid_callback_completes_payment(self, client, db):
        from app.modules.checkout.models import Order, OrderStatus
        from app.modules.payments.models import Payment, PaymentStatus

        # Create a minimal order + payment
        learner = await make_user(db, UserRole.learner, username="pay_learner")
        order = Order(learner_id=learner.id, status=OrderStatus.awaiting_payment, subtotal=100.0, total=100.0, expires_at=datetime.now(UTC) + timedelta(minutes=30))
        db.add(order)
        await db.flush()

        payment = Payment(order_id=order.id, amount=100.0)
        db.add(payment)
        await db.flush()

        from app.core.config import settings
        terminal_ref = "TERM001"
        amount = 100.0
        timestamp = datetime.now(UTC).isoformat()
        message = f"{order.id}{terminal_ref}{amount}{timestamp}"
        sig = hmac.new(settings.PAYMENT_SIGNATURE_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

        resp = await client.post("/api/v1/payments/callback", json={
            "order_id": str(order.id),
            "terminal_ref": terminal_ref,
            "amount": amount,
            "timestamp": timestamp,
            "signature": sig,
        })
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["status"] == "completed"
        assert data["signature_verified"] is True

    async def test_invalid_signature_fails_payment(self, client, db):
        from app.modules.checkout.models import Order, OrderStatus
        from app.modules.payments.models import Payment

        learner = await make_user(db, UserRole.learner, username="pay_learner2")
        order = Order(learner_id=learner.id, status=OrderStatus.awaiting_payment, subtotal=50.0, total=50.0, expires_at=datetime.now(UTC) + timedelta(minutes=30))
        db.add(order)
        await db.flush()

        payment = Payment(order_id=order.id, amount=50.0)
        db.add(payment)
        await db.flush()

        resp = await client.post("/api/v1/payments/callback", json={
            "order_id": str(order.id),
            "terminal_ref": "TERM002",
            "amount": 50.0,
            "timestamp": datetime.now(UTC).isoformat(),
            "signature": "bad-signature",
        })
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["signature_verified"] is False
        assert data["status"] == "failed"
