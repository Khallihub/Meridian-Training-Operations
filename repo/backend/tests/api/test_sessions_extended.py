"""API tests for additional session endpoints: monthly, get, update, delete, complete, recurring."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _setup_session_data(db):
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor

    loc = Location(name="Ext Site", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Ext Room", capacity=30)
    db.add(room)
    course = Course(title="Ext Course", price=100.0, duration_minutes=60)
    db.add(course)
    await db.flush()
    instr_user = await make_user(db, UserRole.instructor, username="ext_instr")
    instr = Instructor(user_id=instr_user.id)
    db.add(instr)
    await db.flush()
    return loc, room, course, instr, instr_user


async def _create_session(client, token, course, instr, room):
    now = datetime.now(UTC)
    payload = {
        "title": "Extended Test Session",
        "course_id": str(course.id),
        "instructor_id": str(instr.id),
        "room_id": str(room.id),
        "start_time": (now + timedelta(days=3)).isoformat(),
        "end_time": (now + timedelta(days=3, hours=1)).isoformat(),
        "capacity": 20,
    }
    resp = await client.post("/api/v1/sessions", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    return resp_data(resp)


@pytest.mark.asyncio
class TestSessionMonthly:
    async def test_list_monthly_calendar(self, client, db):
        await make_user(db, UserRole.admin, username="ext_admin_mo")
        token = await get_token(client, "ext_admin_mo")
        resp = await client.get("/api/v1/sessions/monthly?month=2026-04", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)


@pytest.mark.asyncio
class TestSessionGetUpdateDelete:
    async def test_get_session_by_id(self, client, db):
        loc, room, course, instr, instr_user = await _setup_session_data(db)
        admin = await make_user(db, UserRole.admin, username="ext_admin_get")
        token = await get_token(client, "ext_admin_get")
        session_data = await _create_session(client, token, course, instr, room)

        resp = await client.get(
            f"/api/v1/sessions/{session_data['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["title"] == "Extended Test Session"

    async def test_update_session(self, client, db):
        loc, room, course, instr, instr_user = await _setup_session_data(db)
        admin = await make_user(db, UserRole.admin, username="ext_admin_upd")
        token = await get_token(client, "ext_admin_upd")
        session_data = await _create_session(client, token, course, instr, room)

        resp = await client.patch(
            f"/api/v1/sessions/{session_data['id']}",
            json={"title": "Updated Session Title", "capacity": 30},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["title"] == "Updated Session Title"

    async def test_delete_session(self, client, db):
        loc, room, course, instr, instr_user = await _setup_session_data(db)
        admin = await make_user(db, UserRole.admin, username="ext_admin_del")
        token = await get_token(client, "ext_admin_del")
        session_data = await _create_session(client, token, course, instr, room)

        resp = await client.delete(
            f"/api/v1/sessions/{session_data['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_complete_session(self, client, db):
        loc, room, course, instr, instr_user = await _setup_session_data(db)
        admin = await make_user(db, UserRole.admin, username="ext_admin_cmp")
        token = await get_token(client, "ext_admin_cmp")
        session_data = await _create_session(client, token, course, instr, room)

        # Go live first
        await client.post(
            f"/api/v1/sessions/{session_data['id']}/go-live",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Complete (alias for end)
        resp = await client.post(
            f"/api/v1/sessions/{session_data['id']}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["status"] == "ended"


@pytest.mark.asyncio
class TestRecurringSessions:
    async def test_create_recurring_sessions(self, client, db):
        loc, room, course, instr, instr_user = await _setup_session_data(db)
        admin = await make_user(db, UserRole.admin, username="ext_admin_rec")
        token = await get_token(client, "ext_admin_rec")

        now = datetime.now(UTC)
        payload = {
            "title": "Weekly Python",
            "course_id": str(course.id),
            "instructor_id": str(instr.id),
            "room_id": str(room.id),
            "capacity": 20,
            "buffer_minutes": 10,
            "recurrence": {
                "rrule_string": "FREQ=WEEKLY;COUNT=3",
                "start_date": (now + timedelta(days=7)).isoformat(),
            },
        }
        resp = await client.post(
            "/api/v1/sessions/recurring",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert isinstance(data, list)
        assert len(data) >= 1
