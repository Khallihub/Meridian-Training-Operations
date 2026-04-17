"""API tests for instructors CRUD endpoints."""

import uuid

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="ins_admin")
    return await get_token(client, "ins_admin")


@pytest.mark.asyncio
class TestInstructorsCRUD:
    async def test_create_instructor(self, client, db):
        token = await _admin_token(client, db)
        instr_user = await make_user(db, UserRole.instructor, username="ins_new1")
        resp = await client.post(
            "/api/v1/instructors",
            json={"user_id": str(instr_user.id), "bio": "Expert trainer"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert data["username"] == "ins_new1"
        assert data["bio"] == "Expert trainer"

    async def test_list_instructors(self, client, db):
        token = await _admin_token(client, db)
        instr_user = await make_user(db, UserRole.instructor, username="ins_list1")
        await client.post(
            "/api/v1/instructors",
            json={"user_id": str(instr_user.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get("/api/v1/instructors", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_instructor(self, client, db):
        token = await _admin_token(client, db)
        instr_user = await make_user(db, UserRole.instructor, username="ins_get1")
        create_resp = await client.post(
            "/api/v1/instructors",
            json={"user_id": str(instr_user.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        instr_id = resp_data(create_resp)["id"]
        resp = await client.get(f"/api/v1/instructors/{instr_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp_data(resp)["username"] == "ins_get1"

    async def test_update_instructor(self, client, db):
        token = await _admin_token(client, db)
        instr_user = await make_user(db, UserRole.instructor, username="ins_upd1")
        create_resp = await client.post(
            "/api/v1/instructors",
            json={"user_id": str(instr_user.id), "bio": "Old bio"},
            headers={"Authorization": f"Bearer {token}"},
        )
        instr_id = resp_data(create_resp)["id"]
        resp = await client.patch(
            f"/api/v1/instructors/{instr_id}",
            json={"bio": "Updated bio"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["bio"] == "Updated bio"

    async def test_delete_instructor(self, client, db):
        token = await _admin_token(client, db)
        instr_user = await make_user(db, UserRole.instructor, username="ins_del1")
        create_resp = await client.post(
            "/api/v1/instructors",
            json={"user_id": str(instr_user.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        instr_id = resp_data(create_resp)["id"]
        resp = await client.delete(f"/api/v1/instructors/{instr_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

    async def test_get_nonexistent_instructor_returns_404(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get(f"/api/v1/instructors/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    async def test_learner_cannot_create_instructor(self, client, db):
        await make_user(db, UserRole.learner, username="ins_learner")
        token = await get_token(client, "ins_learner")
        resp = await client.post(
            "/api/v1/instructors",
            json={"user_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
