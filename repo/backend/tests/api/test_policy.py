"""API tests for admin policy endpoints."""

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="pol_admin")
    return await get_token(client, "pol_admin")


@pytest.mark.asyncio
class TestPolicy:
    async def test_get_policy(self, client, db):
        token = await _admin_token(client, db)
        # Ensure a policy row exists
        from app.modules.policy.models import AdminPolicy
        from sqlalchemy import select
        result = await db.execute(select(AdminPolicy))
        if not result.scalar_one_or_none():
            db.add(AdminPolicy())
            await db.flush()

        resp = await client.get("/api/v1/admin/policy", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "reschedule_cutoff_hours" in data
        assert "cancellation_fee_hours" in data

    async def test_update_policy(self, client, db):
        token = await _admin_token(client, db)
        from app.modules.policy.models import AdminPolicy
        from sqlalchemy import select
        result = await db.execute(select(AdminPolicy))
        if not result.scalar_one_or_none():
            db.add(AdminPolicy())
            await db.flush()

        resp = await client.patch(
            "/api/v1/admin/policy",
            json={"reschedule_cutoff_hours": 4, "cancellation_fee_hours": 48},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert data["reschedule_cutoff_hours"] == 4
        assert data["cancellation_fee_hours"] == 48

    async def test_learner_cannot_access_policy(self, client, db):
        await make_user(db, UserRole.learner, username="pol_learner")
        token = await get_token(client, "pol_learner")
        resp = await client.get("/api/v1/admin/policy", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    async def test_learner_cannot_update_policy(self, client, db):
        await make_user(db, UserRole.learner, username="pol_learner2")
        token = await get_token(client, "pol_learner2")
        resp = await client.patch(
            "/api/v1/admin/policy",
            json={"reschedule_cutoff_hours": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
