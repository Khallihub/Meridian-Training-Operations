"""End-to-end user journey tests.

These tests exercise complete multi-step workflows that cross module
boundaries, simulating realistic frontend-to-backend interaction patterns.
Each test represents a user story that spans authentication, CRUD, state
transitions, and data retrieval across multiple API endpoints.
"""

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _full_setup(db):
    """Seed the full domain graph: location, room, course, instructor, admin."""
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor

    loc = Location(name="E2E Campus", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="E2E Room A", capacity=20)
    db.add(room)
    course = Course(title="E2E Python Workshop", price=150.0, duration_minutes=60)
    db.add(course)
    await db.flush()
    instr_user = await make_user(db, UserRole.instructor, username="e2e_instructor")
    instr = Instructor(user_id=instr_user.id, bio="E2E Test Instructor")
    db.add(instr)
    await db.flush()
    admin = await make_user(db, UserRole.admin, username="e2e_admin")
    return loc, room, course, instr, instr_user, admin


@pytest.mark.asyncio
class TestLearnerBookingJourney:
    """Complete learner journey: browse → book → checkout → pay → attend → view replay stats."""

    async def test_full_learner_journey(self, client, db):
        loc, room, course, instr, instr_user, admin = await _full_setup(db)
        learner = await make_user(db, UserRole.learner, username="e2e_learner")
        finance = await make_user(db, UserRole.finance, username="e2e_finance")

        admin_token = await get_token(client, "e2e_admin")
        learner_token = await get_token(client, "e2e_learner")
        instr_token = await get_token(client, "e2e_instructor")
        finance_token = await get_token(client, "e2e_finance")

        # 1. Admin creates a session
        now = datetime.now(UTC)
        create_resp = await client.post("/api/v1/sessions", json={
            "title": "E2E Python Session",
            "course_id": str(course.id),
            "instructor_id": str(instr.id),
            "room_id": str(room.id),
            "start_time": (now + timedelta(days=3)).isoformat(),
            "end_time": (now + timedelta(days=3, hours=1)).isoformat(),
            "capacity": 20,
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert create_resp.status_code == 201
        session_data = resp_data(create_resp)
        session_id = session_data["id"]
        assert session_data["status"] == "scheduled"
        assert session_data["course_title"] == "E2E Python Workshop"

        # 2. Learner browses sessions (weekly calendar)
        week = (now + timedelta(days=3)).strftime("%G-W%V")
        browse_resp = await client.get(
            f"/api/v1/sessions?week={week}",
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert browse_resp.status_code == 200
        sessions = resp_data(browse_resp)
        assert any(s["id"] == session_id for s in sessions)

        # 3. Learner views session detail
        detail_resp = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert detail_resp.status_code == 200
        assert resp_data(detail_resp)["title"] == "E2E Python Session"

        # 4. Learner creates booking
        book_resp = await client.post("/api/v1/bookings", json={
            "session_id": session_id,
        }, headers={"Authorization": f"Bearer {learner_token}"})
        assert book_resp.status_code == 201
        booking = resp_data(book_resp)
        booking_id = booking["id"]
        assert booking["status"] in ("requested", "confirmed")

        # 5. Admin confirms booking
        confirm_resp = await client.patch(
            f"/api/v1/bookings/{booking_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert confirm_resp.status_code == 200
        assert resp_data(confirm_resp)["status"] == "confirmed"

        # 6. Learner checks out (cart + payment)
        cart_resp = await client.post("/api/v1/checkout/cart", json={
            "items": [{"session_id": session_id, "quantity": 1}],
        }, headers={"Authorization": f"Bearer {learner_token}"})
        assert cart_resp.status_code == 201
        order = resp_data(cart_resp)
        order_id = order["id"]
        assert order["total"] > 0
        assert order["status"] == "awaiting_payment"

        # 7. Simulate payment
        pay_resp = await client.post(
            f"/api/v1/payments/{order_id}/simulate",
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert pay_resp.status_code == 200
        payment = resp_data(pay_resp)
        assert payment["status"] in ("completed", "success")

        # 8. Learner views their orders
        orders_resp = await client.get(
            "/api/v1/orders",
            headers={"Authorization": f"Bearer {learner_token}"},
        )
        assert orders_resp.status_code == 200

        # 9. Finance views payment
        fin_pay_resp = await client.get(
            f"/api/v1/payments/{order_id}",
            headers={"Authorization": f"Bearer {finance_token}"},
        )
        assert fin_pay_resp.status_code == 200

        # 10. Admin goes live with session
        live_resp = await client.post(
            f"/api/v1/sessions/{session_id}/go-live",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_data(live_resp)["status"] == "live"

        # 11. Instructor checks in learner
        checkin_resp = await client.post(
            f"/api/v1/sessions/{session_id}/attendance/checkin",
            json={"learner_id": str(learner.id)},
            headers={"Authorization": f"Bearer {instr_token}"},
        )
        assert checkin_resp.status_code == 200

        # 12. Instructor views attendance stats
        stats_resp = await client.get(
            f"/api/v1/sessions/{session_id}/attendance/stats",
            headers={"Authorization": f"Bearer {instr_token}"},
        )
        assert stats_resp.status_code == 200
        stats = resp_data(stats_resp)
        assert stats["checked_in"] >= 1

        # 13. End session
        end_resp = await client.post(
            f"/api/v1/sessions/{session_id}/end",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_data(end_resp)["status"] == "ended"

        # 14. Admin views audit logs for booking
        audit_resp = await client.get(
            f"/api/v1/audit-logs?entity_type=booking&entity_id={booking_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert audit_resp.status_code == 200


@pytest.mark.asyncio
class TestAdminOperationsJourney:
    """Admin journey: setup domain → create session → manage → monitor."""

    async def test_admin_setup_and_management(self, client, db):
        admin = await make_user(db, UserRole.admin, username="e2e_admin2")
        token = await get_token(client, "e2e_admin2")

        # 1. Create location
        loc_resp = await client.post("/api/v1/locations", json={
            "name": "E2E Downtown Center", "address": "456 Oak Ave", "timezone": "UTC",
        }, headers={"Authorization": f"Bearer {token}"})
        assert loc_resp.status_code == 201
        loc_id = resp_data(loc_resp)["id"]

        # 2. Create room in location
        room_resp = await client.post(f"/api/v1/locations/{loc_id}/rooms", json={
            "name": "Training Lab 1", "capacity": 30,
        }, headers={"Authorization": f"Bearer {token}"})
        assert room_resp.status_code == 201
        room_id = resp_data(room_resp)["id"]

        # 3. Create course
        course_resp = await client.post("/api/v1/courses", json={
            "title": "E2E Advanced Python", "price": 200.0, "duration_minutes": 120,
        }, headers={"Authorization": f"Bearer {token}"})
        assert course_resp.status_code == 201
        course_id = resp_data(course_resp)["id"]

        # 4. Create instructor
        instr_user = await make_user(db, UserRole.instructor, username="e2e_instr2")
        instr_resp = await client.post("/api/v1/instructors", json={
            "user_id": str(instr_user.id), "bio": "Senior Python Trainer",
        }, headers={"Authorization": f"Bearer {token}"})
        assert instr_resp.status_code == 201
        instr_id = resp_data(instr_resp)["id"]

        # 5. Create session using all the above
        now = datetime.now(UTC)
        sess_resp = await client.post("/api/v1/sessions", json={
            "title": "E2E Advanced Workshop",
            "course_id": course_id,
            "instructor_id": instr_id,
            "room_id": room_id,
            "start_time": (now + timedelta(days=5)).isoformat(),
            "end_time": (now + timedelta(days=5, hours=2)).isoformat(),
            "capacity": 30,
        }, headers={"Authorization": f"Bearer {token}"})
        assert sess_resp.status_code == 201

        # 6. Verify session appears in monthly calendar
        month = (now + timedelta(days=5)).strftime("%Y-%m")
        cal_resp = await client.get(
            f"/api/v1/sessions/monthly?month={month}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cal_resp.status_code == 200

        # 7. Check monitoring health
        health_resp = await client.get("/api/v1/monitoring/health")
        assert health_resp.status_code == 200
        assert resp_data(health_resp)["status"] == "ok"

        # 8. View metrics
        metrics_resp = await client.get(
            "/api/v1/monitoring/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert metrics_resp.status_code == 200

        # 9. Get policy settings
        policy_resp = await client.get(
            "/api/v1/admin/policy",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert policy_resp.status_code == 200
        assert "reschedule_cutoff_hours" in resp_data(policy_resp)


@pytest.mark.asyncio
class TestRefundJourney:
    """Finance journey: learner pays → requests refund → finance processes full lifecycle."""

    async def test_full_refund_e2e(self, client, db):
        loc, room, course, instr, instr_user, admin = await _full_setup(db)
        learner = await make_user(db, UserRole.learner, username="e2e_rfnd_learner")
        finance = await make_user(db, UserRole.finance, username="e2e_rfnd_finance")

        admin_token = await get_token(client, "e2e_admin")
        learner_token = await get_token(client, "e2e_rfnd_learner")
        finance_token = await get_token(client, "e2e_rfnd_finance")

        # 1. Create session
        now = datetime.now(UTC)
        sess = await client.post("/api/v1/sessions", json={
            "title": "E2E Refund Session",
            "course_id": str(course.id), "instructor_id": str(instr.id),
            "room_id": str(room.id),
            "start_time": (now + timedelta(days=7)).isoformat(),
            "end_time": (now + timedelta(days=7, hours=1)).isoformat(),
        }, headers={"Authorization": f"Bearer {admin_token}"})
        session_id = resp_data(sess)["id"]

        # 2. Learner creates cart and pays
        cart = await client.post("/api/v1/checkout/cart", json={
            "items": [{"session_id": session_id, "quantity": 1}],
        }, headers={"Authorization": f"Bearer {learner_token}"})
        order_id = resp_data(cart)["id"]

        await client.post(
            f"/api/v1/payments/{order_id}/simulate",
            headers={"Authorization": f"Bearer {learner_token}"},
        )

        # 3. Learner requests refund
        rfnd = await client.post("/api/v1/refunds", json={
            "order_id": order_id, "amount": 150.0, "reason": "Session cancelled",
        }, headers={"Authorization": f"Bearer {learner_token}"})
        assert rfnd.status_code == 201
        refund_id = resp_data(rfnd)["id"]

        # 4. Finance walks through full lifecycle
        review = await client.patch(f"/api/v1/refunds/{refund_id}/review",
                                     headers={"Authorization": f"Bearer {finance_token}"})
        assert resp_data(review)["status"] == "pending_review"

        approve = await client.patch(f"/api/v1/refunds/{refund_id}/approve",
                                      headers={"Authorization": f"Bearer {finance_token}"})
        assert resp_data(approve)["status"] == "approved"

        process = await client.patch(f"/api/v1/refunds/{refund_id}/process",
                                      headers={"Authorization": f"Bearer {finance_token}"})
        assert resp_data(process)["status"] == "processing"

        complete = await client.patch(f"/api/v1/refunds/{refund_id}/complete",
                                       headers={"Authorization": f"Bearer {finance_token}"})
        assert resp_data(complete)["status"] == "completed"

        # 5. Finance lists all refunds and verifies
        list_resp = await client.get("/api/v1/refunds",
                                      headers={"Authorization": f"Bearer {finance_token}"})
        assert list_resp.status_code == 200
        refunds = resp_data(list_resp)
        assert any(r["id"] == refund_id and r["status"] == "completed" for r in refunds)
