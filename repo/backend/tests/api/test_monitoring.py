"""API tests for monitoring endpoints."""

import pytest

from tests.conftest import make_user
from app.modules.users.models import UserRole


@pytest.mark.asyncio
class TestMonitoring:
    async def test_health_check(self, client):
        resp = await client.get("/api/monitoring/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_metrics_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/monitoring/metrics")
        assert resp.status_code == 401

    async def test_metrics_endpoint_returns_prometheus_format(self, client, db):
        admin = await make_user(db, UserRole.admin, username="metrics_admin")
        token_resp = await client.post("/api/auth/login", json={"username": "metrics_admin", "password": "TestPass@1234"})
        token = token_resp.json()["access_token"]
        resp = await client.get("/api/monitoring/metrics", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")
