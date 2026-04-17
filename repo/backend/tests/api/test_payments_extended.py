"""API tests for additional payment, refund, and reconciliation endpoints."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _seed_paid_order(db):
    from app.modules.checkout.models import Order, OrderStatus
    from app.modules.payments.models import Payment, PaymentStatus

    learner = await make_user(db, UserRole.learner, username="pay_ext_learner")
    order = Order(
        learner_id=learner.id,
        status=OrderStatus.paid,
        subtotal=300.0,
        total=300.0,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    payment = Payment(order_id=order.id, amount=300.0, status=PaymentStatus.completed)
    db.add(payment)
    await db.flush()
    return learner, order, payment


async def _seed_unpaid_order(db):
    from app.modules.checkout.models import Order, OrderStatus

    learner = await make_user(db, UserRole.learner, username="pay_sim_learner")
    order = Order(
        learner_id=learner.id,
        status=OrderStatus.awaiting_payment,
        subtotal=100.0,
        total=100.0,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(order)
    await db.flush()
    return learner, order


@pytest.mark.asyncio
class TestPaymentsList:
    async def test_finance_can_list_payments(self, client, db):
        await make_user(db, UserRole.finance, username="pay_fin1")
        token = await get_token(client, "pay_fin1")
        resp = await client.get("/api/v1/payments", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body

    async def test_learner_cannot_list_payments(self, client, db):
        await make_user(db, UserRole.learner, username="pay_learn1")
        token = await get_token(client, "pay_learn1")
        resp = await client.get("/api/v1/payments", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestPaymentSimulateAndGet:
    async def test_simulate_payment(self, client, db):
        # Create order via API so data is visible across sessions
        from app.modules.locations.models import Location, Room
        from app.modules.courses.models import Course
        from app.modules.instructors.models import Instructor
        from app.modules.sessions.models import Session
        from datetime import timedelta

        loc = Location(name="PaySim Site", timezone="UTC")
        db.add(loc)
        await db.flush()
        room = Room(location_id=loc.id, name="PaySim Room", capacity=30)
        db.add(room)
        course = Course(title="PaySim Course", price=100.0)
        db.add(course)
        await db.flush()
        instr_user = await make_user(db, UserRole.instructor, username="paysim_instr")
        instr = Instructor(user_id=instr_user.id)
        db.add(instr)
        await db.flush()
        now = datetime.now(UTC)
        session = Session(
            title="PaySim Session", course_id=course.id, instructor_id=instr.id,
            room_id=room.id, start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1), capacity=20, created_by=instr_user.id,
        )
        db.add(session)
        await db.flush()

        learner = await make_user(db, UserRole.learner, username="pay_sim_learner")
        token = await get_token(client, "pay_sim_learner")

        cart_resp = await client.post(
            "/api/v1/checkout/cart",
            json={"items": [{"session_id": str(session.id), "quantity": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cart_resp.status_code == 201
        order_id = resp_data(cart_resp)["id"]

        resp = await client.post(
            f"/api/v1/payments/{order_id}/simulate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "amount" in data
        assert "status" in data

    async def test_get_payment_by_order(self, client, db):
        learner, order, payment = await _seed_paid_order(db)
        finance = await make_user(db, UserRole.finance, username="pay_fin2")
        token = await get_token(client, "pay_fin2")
        resp = await client.get(
            f"/api/v1/payments/{order.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert float(data["amount"]) == 300.0
        assert data["status"] == "completed"


@pytest.mark.asyncio
class TestRefundsList:
    async def test_list_refunds(self, client, db):
        finance = await make_user(db, UserRole.finance, username="pay_rfnd_fin1")
        token = await get_token(client, "pay_rfnd_fin1")
        resp = await client.get("/api/v1/refunds", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)

    async def test_list_refunds_with_status_filter(self, client, db):
        finance = await make_user(db, UserRole.finance, username="pay_rfnd_fin2")
        token = await get_token(client, "pay_rfnd_fin2")
        resp = await client.get("/api/v1/refunds?status=requested", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)

    async def test_get_refund_by_id(self, client, db):
        learner, order, payment = await _seed_paid_order(db)
        finance = await make_user(db, UserRole.finance, username="pay_rfnd_fin3")
        learner_token = await get_token(client, "pay_ext_learner")
        finance_token = await get_token(client, "pay_rfnd_fin3")

        create_resp = await client.post(
            "/api/v1/refunds",
            json={"order_id": str(order.id), "amount": 300.0, "reason": "Test"},
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert create_resp.status_code == 201
        refund_id = resp_data(create_resp)["id"]

        resp = await client.get(
            f"/api/v1/refunds/{refund_id}",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["status"] == "requested"
        assert float(data["amount"]) == 300.0


@pytest.mark.asyncio
class TestReconciliation:
    async def test_trigger_reconciliation_export(self, client, db):
        finance = await make_user(db, UserRole.finance, username="pay_recon_fin1")
        token = await get_token(client, "pay_recon_fin1")
        # Ensure exports directory exists for test
        os.makedirs("/app/exports", exist_ok=True)
        resp = await client.post(
            "/api/v1/reconciliation/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "export_date" in data
        assert "row_count" in data

    async def test_get_reconciliation_export(self, client, db):
        finance = await make_user(db, UserRole.finance, username="pay_recon_fin2")
        token = await get_token(client, "pay_recon_fin2")
        os.makedirs("/app/exports", exist_ok=True)
        resp = await client.get(
            "/api/v1/reconciliation/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "export_date" in data

    async def test_list_reconciliation_exports(self, client, db):
        finance = await make_user(db, UserRole.finance, username="pay_recon_fin3")
        token = await get_token(client, "pay_recon_fin3")
        resp = await client.get(
            "/api/v1/reconciliation/exports",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)

    async def test_download_nonexistent_export_returns_404(self, client, db):
        finance = await make_user(db, UserRole.finance, username="pay_recon_fin4")
        token = await get_token(client, "pay_recon_fin4")
        resp = await client.get(
            f"/api/v1/reconciliation/exports/{uuid.uuid4()}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_download_existing_export_returns_csv(self, client, db):
        """Happy path: create export then download the CSV file."""
        finance = await make_user(db, UserRole.finance, username="pay_recon_fin5")
        token = await get_token(client, "pay_recon_fin5")
        os.makedirs("/app/exports", exist_ok=True)

        # Trigger export to create an export record with a file
        create_resp = await client.post(
            "/api/v1/reconciliation/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_resp.status_code == 200
        export_data = resp_data(create_resp)
        export_id = export_data["id"]

        # Download the export
        dl_resp = await client.get(
            f"/api/v1/reconciliation/exports/{export_id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dl_resp.status_code == 200
        assert "text/csv" in dl_resp.headers.get("content-type", "")

    async def test_learner_cannot_access_reconciliation(self, client, db):
        await make_user(db, UserRole.learner, username="pay_recon_learn")
        token = await get_token(client, "pay_recon_learn")
        resp = await client.get("/api/v1/reconciliation/exports", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
