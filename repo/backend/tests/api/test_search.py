"""API tests for search, saved searches, and export job endpoints."""

import os
import uuid

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="srch_admin")
    return await get_token(client, "srch_admin")


@pytest.mark.asyncio
class TestSearch:
    async def test_admin_can_search(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.post(
            "/api/v1/search",
            json={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp_data(resp)
        assert "results" in data or "total_count" in data

    async def test_instructor_can_search(self, client, db):
        await make_user(db, UserRole.instructor, username="srch_instr")
        token = await get_token(client, "srch_instr")
        resp = await client.post(
            "/api/v1/search",
            json={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_learner_cannot_search(self, client, db):
        await make_user(db, UserRole.learner, username="srch_learner")
        token = await get_token(client, "srch_learner")
        resp = await client.post(
            "/api/v1/search",
            json={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestSavedSearches:
    async def test_list_saved_searches(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get("/api/v1/search/saved", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)

    async def test_save_search(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.post(
            "/api/v1/search/saved",
            json={"name": "My Search", "filters": {"enrollment_status": "confirmed"}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert data["name"] == "My Search"

    async def test_delete_saved_search(self, client, db):
        token = await _admin_token(client, db)
        # Create a saved search first
        create_resp = await client.post(
            "/api/v1/search/saved",
            json={"name": "To Delete", "filters": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        search_id = resp_data(create_resp)["id"]

        resp = await client.delete(
            f"/api/v1/search/saved/{search_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestSearchExportJobs:
    async def test_create_export_job(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.post(
            "/api/v1/search/export/jobs",
            json={"filters": {"page": 1, "page_size": 10}, "format": "csv"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        data = resp_data(resp)
        assert data["status"] == "queued"
        assert data["format"] == "csv"

    async def test_get_export_job_not_found(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get(
            f"/api/v1/search/export/jobs/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_download_export_not_found(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get(
            f"/api/v1/search/export/jobs/{uuid.uuid4()}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_get_completed_export_job(self, client, db):
        """Happy path: seed a completed export job and verify retrieval."""
        import os
        from app.modules.search.models import SearchExportJob, SearchExportJobStatus
        from datetime import UTC, datetime

        admin = await make_user(db, UserRole.admin, username="srch_dl_admin")
        token = await get_token(client, "srch_dl_admin")

        # Seed a completed export job with a real file
        os.makedirs("/app/exports", exist_ok=True)
        file_path = "/app/exports/test_search_export.csv"
        with open(file_path, "w") as f:
            f.write("booking_id,session_id,status\nb1,s1,confirmed\n")

        job = SearchExportJob(
            status=SearchExportJobStatus.completed,
            format="csv",
            filters_json={"page": 1},
            file_path=file_path,
            row_count=1,
            caller_role="admin",
            caller_id=admin.id,
            created_by=admin.id,
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        await db.flush()

        # GET job status — should show completed
        status_resp = await client.get(
            f"/api/v1/search/export/jobs/{job.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_resp.status_code == 200
        data = resp_data(status_resp)
        assert data["status"] == "completed"
        assert data["row_count"] == 1

        # Download the file
        dl_resp = await client.get(
            f"/api/v1/search/export/jobs/{job.id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dl_resp.status_code == 200
        assert "csv" in dl_resp.headers.get("content-type", "")

    async def test_learner_cannot_create_export(self, client, db):
        await make_user(db, UserRole.learner, username="srch_exp_learner")
        token = await get_token(client, "srch_exp_learner")
        resp = await client.post(
            "/api/v1/search/export/jobs",
            json={"filters": {}, "format": "csv"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
