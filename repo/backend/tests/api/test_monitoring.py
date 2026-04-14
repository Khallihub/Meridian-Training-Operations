"""API tests for monitoring endpoints."""

import pytest

from tests.conftest import make_user, resp_data
from app.modules.users.models import UserRole


@pytest.mark.asyncio
class TestMonitoring:
    async def test_health_check(self, client):
        resp = await client.get("/api/v1/monitoring/health")
        assert resp.status_code == 200
        assert resp_data(resp)["status"] == "ok"

    async def test_metrics_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/v1/monitoring/metrics")
        assert resp.status_code == 401

    async def test_metrics_endpoint_returns_prometheus_format(self, client, db):
        admin = await make_user(db, UserRole.admin, username="metrics_admin")
        token_resp = await client.post("/api/v1/auth/login", json={"username": "metrics_admin", "password": "TestPass@1234"})
        token = resp_data(token_resp)["access_token"]
        resp = await client.get("/api/v1/monitoring/metrics", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")
