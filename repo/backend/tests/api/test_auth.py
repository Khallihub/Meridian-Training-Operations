"""API tests for authentication endpoints."""

import pytest
import pytest_asyncio

from tests.conftest import make_user
from app.modules.users.models import UserRole


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client, db):
        user = await make_user(db, UserRole.admin, username="test_admin")
        resp = await client.post("/api/auth/login", json={"username":"test_admin", "password":"TestPass@1234"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client, db):
        await make_user(db, username="user_wrong_pw")
        resp = await client.post("/api/auth/login", json={"username":"user_wrong_pw", "password":"WrongPass@1"})
        assert resp.status_code == 401

    async def test_login_unknown_user(self, client):
        resp = await client.post("/api/auth/login", json={"username":"nobody", "password":"X"})
        assert resp.status_code == 401

    async def test_account_lockout_after_5_failures(self, client, db):
        await make_user(db, username="lockout_user")
        for _ in range(5):
            await client.post("/api/auth/login", json={"username":"lockout_user", "password":"Bad@Pass1234"})
        resp = await client.post("/api/auth/login", json={"username":"lockout_user", "password":"Bad@Pass1234"})
        assert resp.status_code == 423
        data = resp.json()
        assert "locked" in data["detail"].lower()
        assert "locked_until" in data.get("errors", {})


@pytest.mark.asyncio
class TestProtectedEndpoints:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/users/me")
        assert resp.status_code == 401

    async def test_authenticated_returns_user(self, client, db):
        user = await make_user(db, UserRole.admin, username="me_user")
        token_resp = await client.post("/api/auth/login", json={"username":"me_user", "password":"TestPass@1234"})
        token = token_resp.json()["access_token"]
        resp = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "me_user"


@pytest.mark.asyncio
class TestChangePassword:
    async def test_change_password_success(self, client, db):
        await make_user(db, username="pw_changer")
        token_resp = await client.post("/api/auth/login", json={"username":"pw_changer", "password":"TestPass@1234"})
        token = token_resp.json()["access_token"]
        resp = await client.post(
            "/api/auth/change-password",
            json={"current_password": "TestPass@1234", "new_password": "NewSecure@5678"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_change_password_wrong_current(self, client, db):
        await make_user(db, username="pw_fail_user")
        token_resp = await client.post("/api/auth/login", json={"username":"pw_fail_user", "password":"TestPass@1234"})
        token = token_resp.json()["access_token"]
        resp = await client.post(
            "/api/auth/change-password",
            json={"current_password": "WrongCurrent@1234", "new_password": "NewSecure@5678"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
