"""API tests for auth refresh and logout endpoints."""

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


@pytest.mark.asyncio
class TestAuthRefresh:
    async def test_refresh_token(self, client, db):
        await make_user(db, UserRole.admin, username="auth_ref1")
        # Login to get refresh token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "auth_ref1", "password": "TestPass@1234"},
        )
        assert login_resp.status_code == 200
        tokens = resp_data(login_resp)
        refresh_token = tokens["refresh_token"]

        # Use refresh token to get new access token
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_with_invalid_token(self, client, db):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token-string"},
        )
        assert resp.status_code in (401, 422)


@pytest.mark.asyncio
class TestAuthLogout:
    async def test_logout(self, client, db):
        await make_user(db, UserRole.admin, username="auth_logout1")
        token = await get_token(client, "auth_logout1")
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_logout_without_auth_returns_401(self, client, db):
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code in (401, 403)
