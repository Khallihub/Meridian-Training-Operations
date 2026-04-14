"""API tests for replay authorization matrix."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import make_user, resp_data
from app.modules.users.models import UserRole


async def _seed_session_with_instructor(db, instructor_user_id: uuid.UUID):
    from app.modules.locations.models import Location, Room
    from app.modules.courses.models import Course
    from app.modules.instructors.models import Instructor
    from app.modules.sessions.models import Session

    loc = Location(name="Replay Site", timezone="UTC")
    db.add(loc)
    await db.flush()
    room = Room(location_id=loc.id, name="Replay Room", capacity=20)
    db.add(room)
    course = Course(title="Replay Course", price=80.0, duration_minutes=60)
    db.add(course)
    await db.flush()
    instructor = Instructor(user_id=instructor_user_id)
    db.add(instructor)
    await db.flush()
    now = datetime.now(UTC)
    session = Session(
        title="Replay Session",
        course_id=course.id,
        instructor_id=instructor.id,
        room_id=room.id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=instructor_user_id,
    )
    db.add(session)
    await db.flush()
    return session, instructor


async def _token(client, username: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": "TestPass@1234"})
    return resp_data(resp)["access_token"]


@pytest.mark.asyncio
class TestReplayAuthMatrix:
    async def test_learner_cannot_initiate_upload(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr1")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        learner = await make_user(db, UserRole.learner, username="rp_learn1")
        token = await _token(client, "rp_learn1")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/replay/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unassigned_instructor_cannot_initiate_upload(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr2")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        other = await make_user(db, UserRole.instructor, username="rp_instr2b")
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()
        token = await _token(client, "rp_instr2b")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/replay/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_assigned_instructor_can_initiate_upload(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr3")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        token = await _token(client, "rp_instr3")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/replay/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 200 if MinIO reachable; 500/422 on infra error — both prove auth passed
        assert resp.status_code != 403

    async def test_admin_can_initiate_upload(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr4")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        admin = await make_user(db, UserRole.admin, username="rp_admin4")
        token = await _token(client, "rp_admin4")
        resp = await client.post(
            f"/api/v1/sessions/{session.id}/replay/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 403

    async def test_unassigned_instructor_cannot_confirm_upload(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr5")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        other = await make_user(db, UserRole.instructor, username="rp_instr5b")
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()
        token = await _token(client, "rp_instr5b")
        resp = await client.patch(
            f"/api/v1/sessions/{session.id}/replay/recording",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unassigned_instructor_cannot_view_stats(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr6")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        other = await make_user(db, UserRole.instructor, username="rp_instr6b")
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()
        token = await _token(client, "rp_instr6b")
        resp = await client.get(
            f"/api/v1/replays/{session.id}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_assigned_instructor_can_view_stats(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr7")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        token = await _token(client, "rp_instr7")
        resp = await client.get(
            f"/api/v1/replays/{session.id}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_learner_cannot_view_stats(self, client, db):
        owner = await make_user(db, UserRole.instructor, username="rp_instr8")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        learner = await make_user(db, UserRole.learner, username="rp_learn8")
        token = await _token(client, "rp_learn8")
        resp = await client.get(
            f"/api/v1/replays/{session.id}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_replay(self, client, db):
        session_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/sessions/{session_id}/replay")
        assert resp.status_code == 401

    # ------------------------------------------------------------------
    # Replay read-path object-level authorization (H-01 regression gate)
    # ------------------------------------------------------------------

    async def test_unassigned_instructor_cannot_get_replay(self, client, db):
        """An instructor not assigned to a session must be denied replay read (403)."""
        owner = await make_user(db, UserRole.instructor, username="rp_rd_instr1")
        session, _ = await _seed_session_with_instructor(db, owner.id)

        other = await make_user(db, UserRole.instructor, username="rp_rd_instr1b")
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()

        token = await _token(client, "rp_rd_instr1b")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/replay",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_assigned_instructor_can_get_replay(self, client, db):
        """The assigned instructor may access the replay (auth passes; 404 acceptable if no recording)."""
        owner = await make_user(db, UserRole.instructor, username="rp_rd_instr2")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        token = await _token(client, "rp_rd_instr2")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/replay",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 404 = no recording seeded yet; either way auth must have passed (not 403)
        assert resp.status_code != 403

    async def test_unassigned_instructor_cannot_list_recordings(self, client, db):
        """An instructor not assigned to the session must be denied the recordings list (403)."""
        owner = await make_user(db, UserRole.instructor, username="rp_rd_instr3")
        session, _ = await _seed_session_with_instructor(db, owner.id)

        other = await make_user(db, UserRole.instructor, username="rp_rd_instr3b")
        from app.modules.instructors.models import Instructor
        db.add(Instructor(user_id=other.id))
        await db.flush()

        token = await _token(client, "rp_rd_instr3b")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/recordings",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_assigned_instructor_can_list_recordings(self, client, db):
        """The assigned instructor may list recordings for their session."""
        owner = await make_user(db, UserRole.instructor, username="rp_rd_instr4")
        session, _ = await _seed_session_with_instructor(db, owner.id)
        token = await _token(client, "rp_rd_instr4")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/recordings",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 403

    async def test_instructor_without_record_cannot_get_replay(self, client, db):
        """An instructor user with no Instructor row must be denied replay read (403)."""
        owner = await make_user(db, UserRole.instructor, username="rp_rd_instr5")
        session, _ = await _seed_session_with_instructor(db, owner.id)

        # This instructor user has no Instructor row
        no_rec = await make_user(db, UserRole.instructor, username="rp_rd_instr5b")
        token = await _token(client, "rp_rd_instr5b")
        resp = await client.get(
            f"/api/v1/sessions/{session.id}/replay",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
