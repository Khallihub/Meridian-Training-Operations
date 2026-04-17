"""API tests for audit log endpoint."""

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


@pytest.mark.asyncio
class TestAuditLogs:
    async def test_admin_can_list_audit_logs(self, client, db):
        await make_user(db, UserRole.admin, username="aud_admin")
        token = await get_token(client, "aud_admin")
        resp = await client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        # Paginated response
        assert "meta" in body or "data" in body

    async def test_audit_logs_with_filters(self, client, db):
        await make_user(db, UserRole.admin, username="aud_admin2")
        token = await get_token(client, "aud_admin2")
        resp = await client.get(
            "/api/v1/audit-logs?entity_type=user&page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_learner_cannot_access_audit_logs(self, client, db):
        await make_user(db, UserRole.learner, username="aud_learner")
        token = await get_token(client, "aud_learner")
        resp = await client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    async def test_finance_cannot_access_audit_logs(self, client, db):
        await make_user(db, UserRole.finance, username="aud_finance")
        token = await get_token(client, "aud_finance")
        resp = await client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
