"""API tests for sessions."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import make_user
from app.modules.users.models import UserRole


async def _setup_session_data(db):
    """Create location, room, course, instructor, return their IDs."""
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor

    loc = Location(name="Test Site", timezone="UTC")
    db.add(loc)
    await db.flush()

    room = Room(location_id=loc.id, name="Room A", capacity=20)
    db.add(room)

    course = Course(title="Python Basics", price=100.0, duration_minutes=60)
    db.add(course)
    await db.flush()

    instructor_user = await make_user(db, UserRole.instructor, username="instr_sess")
    instructor = Instructor(user_id=instructor_user.id)
    db.add(instructor)
    await db.flush()

    return loc, room, course, instructor, instructor_user


@pytest.mark.asyncio
class TestSessionCRUD:
    async def test_create_session(self, client, db):
        loc, room, course, instructor, instr_user = await _setup_session_data(db)
        admin = await make_user(db, UserRole.admin, username="admin_sess")
        token_resp = await client.post("/api/auth/login", json={"username": "admin_sess", "password": "TestPass@1234"})
        token = token_resp.json()["access_token"]

        now = datetime.now(UTC)
        payload = {
            "course_id": str(course.id),
            "instructor_id": str(instructor.id),
            "room_id": str(room.id),
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=1)).isoformat(),
            "capacity": 20,
        }
        resp = await client.post("/api/sessions", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "scheduled"

    async def test_get_weekly_calendar(self, client, db):
        admin = await make_user(db, UserRole.admin, username="admin_cal")
        token_resp = await client.post("/api/auth/login", json={"username": "admin_cal", "password": "TestPass@1234"})
        token = token_resp.json()["access_token"]
        resp = await client.get("/api/sessions?week=2026-W14", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_go_live_and_complete(self, client, db):
        loc, room, course, instructor, instr_user = await _setup_session_data(db)
        admin = await make_user(db, UserRole.admin, username="admin_live")
        token_resp = await client.post("/api/auth/login", json={"username": "admin_live", "password": "TestPass@1234"})
        token = token_resp.json()["access_token"]

        now = datetime.now(UTC)
        payload = {
            "course_id": str(course.id),
            "instructor_id": str(instructor.id),
            "room_id": str(room.id),
            "start_time": (now + timedelta(minutes=5)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        }
        create_resp = await client.post("/api/sessions", json=payload, headers={"Authorization": f"Bearer {token}"})
        session_id = create_resp.json()["id"]

        live_resp = await client.post(f"/api/sessions/{session_id}/go-live", headers={"Authorization": f"Bearer {token}"})
        assert live_resp.json()["status"] == "live"

        complete_resp = await client.post(f"/api/sessions/{session_id}/complete", headers={"Authorization": f"Bearer {token}"})
        assert complete_resp.json()["status"] == "completed"
