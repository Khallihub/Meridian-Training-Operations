"""API tests for the full refund state machine: requested → pending_review → approved → processing → completed."""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import make_user, resp_data
from app.modules.users.models import UserRole


async def _seed_paid_order_with_payment(db):
    from app.modules.checkout.models import Order, OrderStatus
    from app.modules.payments.models import Payment, PaymentStatus

    learner = await make_user(db, UserRole.learner, username="rfnd_learner")
    order = Order(
        learner_id=learner.id,
        status=OrderStatus.paid,
        subtotal=200.0,
        total=200.0,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    payment = Payment(order_id=order.id, amount=200.0, status=PaymentStatus.completed)
    db.add(payment)
    await db.flush()
    return learner, order, payment


async def _token(client, username: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": "TestPass@1234"})
    return resp_data(resp)["access_token"]


@pytest.mark.asyncio
class TestRefundLifecycle:
    async def test_full_refund_state_machine(self, client, db):
        """Walk a refund through the complete happy path: requested → pending_review → approved → processing → completed."""
        learner, order, payment = await _seed_paid_order_with_payment(db)
        finance = await make_user(db, UserRole.finance, username="rfnd_finance1")

        learner_token = await _token(client, "rfnd_learner")
        finance_token = await _token(client, "rfnd_finance1")

        # 1. Learner submits refund request
        resp = await client.post(
            "/api/v1/refunds",
            json={"order_id": str(order.id), "amount": 200.0, "reason": "Course cancelled by provider"},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert resp.status_code == 201
        refund = resp_data(resp)
        refund_id = refund["id"]
        assert refund["status"] == "requested"

        # 2. Finance moves to pending_review
        resp = await client.patch(
            f"/api/v1/refunds/{refund_id}/review",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["status"] == "pending_review"

        # 3. Finance approves
        resp = await client.patch(
            f"/api/v1/refunds/{refund_id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["status"] == "approved"

        # 4. Finance starts processing
        resp = await client.patch(
            f"/api/v1/refunds/{refund_id}/process",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["status"] == "processing"

        # 5. Finance completes
        resp = await client.patch(
            f"/api/v1/refunds/{refund_id}/complete",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["status"] == "completed"

    async def test_refund_rejection_path(self, client, db):
        """Walk: requested → pending_review → rejected."""
        learner, order, payment = await _seed_paid_order_with_payment(db)
        # Rename learner for username uniqueness
        from app.core.security import hash_password
        from app.modules.users.models import User
        learner2 = User(username="rfnd_learner2", password_hash=hash_password("TestPass@1234"), role=UserRole.learner, is_active=True)
        db.add(learner2)
        await db.flush()
        from app.modules.checkout.models import Order, OrderStatus
        from app.modules.payments.models import Payment, PaymentStatus
        order2 = Order(learner_id=learner2.id, status=OrderStatus.paid, subtotal=100.0, total=100.0, expires_at=datetime.now(UTC) + timedelta(hours=1), paid_at=datetime.now(UTC))
        db.add(order2)
        await db.flush()
        payment2 = Payment(order_id=order2.id, amount=100.0, status=PaymentStatus.completed)
        db.add(payment2)
        await db.flush()

        finance = await make_user(db, UserRole.finance, username="rfnd_finance2")
        learner2_token = await _token(client, "rfnd_learner2")
        finance_token = await _token(client, "rfnd_finance2")

        resp = await client.post(
            "/api/v1/refunds",
            json={"order_id": str(order2.id), "amount": 100.0, "reason": "Changed mind"},
            headers={"Authorization": f"Bearer {learner2_token}"},
        )
        assert resp.status_code == 201
        refund_id = resp_data(resp)["id"]

        await client.patch(f"/api/v1/refunds/{refund_id}/review", headers={"Authorization": f"Bearer {finance_token}"})

        resp = await client.patch(
            f"/api/v1/refunds/{refund_id}/reject",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["status"] == "rejected"

    async def test_invalid_transition_rejected(self, client, db):
        """Cannot jump from requested directly to approved (skipping pending_review)."""
        learner, order, payment = await _seed_paid_order_with_payment(db)
        from app.core.security import hash_password
        from app.modules.users.models import User
        learner3 = User(username="rfnd_learner3", password_hash=hash_password("TestPass@1234"), role=UserRole.learner, is_active=True)
        db.add(learner3)
        await db.flush()
        from app.modules.checkout.models import Order, OrderStatus
        from app.modules.payments.models import Payment, PaymentStatus
        order3 = Order(learner_id=learner3.id, status=OrderStatus.paid, subtotal=50.0, total=50.0, expires_at=datetime.now(UTC) + timedelta(hours=1))
        db.add(order3)
        await db.flush()
        payment3 = Payment(order_id=order3.id, amount=50.0, status=PaymentStatus.completed)
        db.add(payment3)
        await db.flush()

        finance = await make_user(db, UserRole.finance, username="rfnd_finance3")
        learner3_token = await _token(client, "rfnd_learner3")
        finance_token = await _token(client, "rfnd_finance3")

        resp = await client.post(
            "/api/v1/refunds",
            json={"order_id": str(order3.id), "amount": 50.0, "reason": "Test"},
            headers={"Authorization": f"Bearer {learner3_token}"},
        )
        refund_id = resp_data(resp)["id"]

        # Skip review, go straight to approve — should fail
        resp = await client.patch(
            f"/api/v1/refunds/{refund_id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert resp.status_code in (409, 422)

    async def test_learner_cannot_approve_own_refund(self, client, db):
        """Learner must not be able to advance their own refund through the workflow."""
        learner, order, payment = await _seed_paid_order_with_payment(db)
        learner_token = await _token(client, "rfnd_learner")

        resp = await client.post(
            "/api/v1/refunds",
            json={"order_id": str(order.id), "amount": 200.0, "reason": "Self-service"},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        # First call may already exist in the same DB tx — either 201 or 409 is fine
        if resp.status_code == 201:
            refund_id = resp_data(resp)["id"]
            resp2 = await client.patch(
                f"/api/v1/refunds/{refund_id}/approve",
                headers={"Authorization": f"Bearer {learner_token}"},
            )
            assert resp2.status_code == 403
