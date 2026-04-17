"""API tests for additional ingestion endpoints: source CRUD, test-connection, trigger, runs."""

import uuid

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="ige_admin")
    return await get_token(client, "ige_admin")


async def _dataops_token(client, db):
    await make_user(db, UserRole.dataops, username="ige_dataops")
    return await get_token(client, "ige_dataops")


async def _create_source(client, token, name="Test Source"):
    resp = await client.post(
        "/api/v1/ingestion/sources",
        json={"name": name, "type": "kafka", "collection_frequency_seconds": 60, "concurrency_cap": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


@pytest.mark.asyncio
class TestIngestionSourceCRUD:
    async def test_get_source(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await _create_source(client, token, "Get Source")
        source_id = resp_data(create_resp)["id"]

        resp = await client.get(
            f"/api/v1/ingestion/sources/{source_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["name"] == "Get Source"

    async def test_update_source(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await _create_source(client, token, "Upd Source")
        source_id = resp_data(create_resp)["id"]

        resp = await client.patch(
            f"/api/v1/ingestion/sources/{source_id}",
            json={"name": "Updated Source", "collection_frequency_seconds": 120},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["name"] == "Updated Source"

    async def test_delete_source(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await _create_source(client, token, "Del Source")
        source_id = resp_data(create_resp)["id"]

        resp = await client.delete(
            f"/api/v1/ingestion/sources/{source_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_dataops_can_manage_sources(self, client, db):
        token = await _dataops_token(client, db)
        create_resp = await _create_source(client, token, "Dataops Source")
        assert create_resp.status_code == 201
        source_id = resp_data(create_resp)["id"]

        resp = await client.get(
            f"/api/v1/ingestion/sources/{source_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestIngestionActions:
    async def test_test_connection(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await _create_source(client, token, "Conn Source")
        source_id = resp_data(create_resp)["id"]

        resp = await client.post(
            f"/api/v1/ingestion/sources/{source_id}/test-connection",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "success" in data

    async def test_trigger_run(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await _create_source(client, token, "Trigger Source")
        source_id = resp_data(create_resp)["id"]

        resp = await client.post(
            f"/api/v1/ingestion/sources/{source_id}/trigger",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "source_id" in data
        assert "status" in data

    async def test_list_runs(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await _create_source(client, token, "Runs Source")
        source_id = resp_data(create_resp)["id"]

        resp = await client.get(
            f"/api/v1/ingestion/sources/{source_id}/runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)

    async def test_get_run_not_found(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get(
            f"/api/v1/ingestion/runs/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
