"""API tests for additional monitoring endpoints: scrape, alerts, resolve."""

import os
from datetime import UTC, datetime

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


@pytest.mark.asyncio
class TestMetricsScrape:
    async def test_scrape_with_valid_token(self, client, db):
        scrape_token = os.environ.get("PROMETHEUS_SCRAPE_TOKEN", "change-me-prometheus-scrape-token")
        resp = await client.get(
            "/api/v1/monitoring/metrics/scrape",
            headers={"Authorization": f"Bearer {scrape_token}"},
        )
        assert resp.status_code == 200

    async def test_scrape_without_token_returns_401(self, client, db):
        resp = await client.get("/api/v1/monitoring/metrics/scrape")
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body or "detail" in body

    async def test_scrape_with_invalid_token_returns_401(self, client, db):
        resp = await client.get(
            "/api/v1/monitoring/metrics/scrape",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body or "detail" in body


@pytest.mark.asyncio
class TestAlerts:
    async def test_list_alerts(self, client, db):
        await make_user(db, UserRole.admin, username="mon_admin1")
        token = await get_token(client, "mon_admin1")
        resp = await client.get("/api/v1/monitoring/alerts", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)

    async def test_list_alerts_resolved_filter(self, client, db):
        await make_user(db, UserRole.admin, username="mon_admin2")
        token = await get_token(client, "mon_admin2")
        resp = await client.get(
            "/api/v1/monitoring/alerts?resolved=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_resolve_alert(self, client, db):
        # Seed an alert
        from app.modules.jobs.models import MonitoringAlert
        alert = MonitoringAlert(
            alert_type="failure_rate",
            message="Job test-job exceeded failure threshold",
            job_name="test-job",
            is_resolved=False,
        )
        db.add(alert)
        await db.flush()

        await make_user(db, UserRole.admin, username="mon_admin3")
        token = await get_token(client, "mon_admin3")
        resp = await client.patch(
            f"/api/v1/monitoring/alerts/{alert.id}/resolve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_dataops_can_manage_alerts(self, client, db):
        await make_user(db, UserRole.dataops, username="mon_dataops1")
        token = await get_token(client, "mon_dataops1")
        resp = await client.get("/api/v1/monitoring/alerts", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_learner_cannot_access_alerts(self, client, db):
        await make_user(db, UserRole.learner, username="mon_learner1")
        token = await get_token(client, "mon_learner1")
        resp = await client.get("/api/v1/monitoring/alerts", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
