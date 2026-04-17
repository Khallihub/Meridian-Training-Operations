"""API tests for user CRUD endpoints."""

import uuid

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="usr_admin")
    return await get_token(client, "usr_admin")


@pytest.mark.asyncio
class TestUserList:
    async def test_admin_can_list_users(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body or "items" in body or isinstance(body, list) or "meta" in body

    async def test_learner_cannot_list_users(self, client, db):
        await make_user(db, UserRole.learner, username="usr_learner1")
        token = await get_token(client, "usr_learner1")
        resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    async def test_list_users_filter_by_role(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get("/api/v1/users?role=admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestUserCreate:
    async def test_admin_can_create_user(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.post(
            "/api/v1/users",
            json={
                "username": f"newuser_{uuid.uuid4().hex[:8]}",
                "password": "StrongPass@1234",
                "role": "learner",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert data["role"] == "learner"

    async def test_learner_cannot_create_user(self, client, db):
        await make_user(db, UserRole.learner, username="usr_learner2")
        token = await get_token(client, "usr_learner2")
        resp = await client.post(
            "/api/v1/users",
            json={"username": "x", "password": "StrongPass@1234", "role": "learner"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestUserGetUpdateDelete:
    async def test_get_user_by_id(self, client, db):
        target = await make_user(db, UserRole.learner, username="usr_target1")
        token = await _admin_token(client, db)
        resp = await client.get(f"/api/v1/users/{target.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp_data(resp)["username"] == "usr_target1"

    async def test_non_admin_cannot_view_others(self, client, db):
        target = await make_user(db, UserRole.learner, username="usr_target2")
        other = await make_user(db, UserRole.learner, username="usr_other2")
        token = await get_token(client, "usr_other2")
        resp = await client.get(f"/api/v1/users/{target.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    async def test_user_can_view_self(self, client, db):
        user = await make_user(db, UserRole.learner, username="usr_self1")
        token = await get_token(client, "usr_self1")
        resp = await client.get(f"/api/v1/users/{user.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_update_user(self, client, db):
        target = await make_user(db, UserRole.learner, username="usr_upd1")
        token = await _admin_token(client, db)
        resp = await client.patch(
            f"/api/v1/users/{target.id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_delete_user(self, client, db):
        target = await make_user(db, UserRole.learner, username="usr_del1")
        token = await _admin_token(client, db)
        resp = await client.delete(f"/api/v1/users/{target.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

    async def test_unmask_user_pii(self, client, db):
        target = await make_user(db, UserRole.learner, username="usr_unmask1")
        token = await _admin_token(client, db)
        resp = await client.post(
            f"/api/v1/users/{target.id}/unmask?reason=Support+ticket+investigation",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
