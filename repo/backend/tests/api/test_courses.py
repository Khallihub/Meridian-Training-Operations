"""API tests for courses CRUD endpoints."""

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="crs_admin")
    return await get_token(client, "crs_admin")


@pytest.mark.asyncio
class TestCoursesCRUD:
    async def test_create_course(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.post(
            "/api/v1/courses",
            json={"title": "Intro to Python", "description": "Beginner course", "duration_minutes": 90, "price": 99.99},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert data["title"] == "Intro to Python"
        assert data["price"] == 99.99

    async def test_list_courses(self, client, db):
        token = await _admin_token(client, db)
        await client.post(
            "/api/v1/courses",
            json={"title": "List Course", "price": 50.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get("/api/v1/courses", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_list_courses_filter_active(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.get("/api/v1/courses?is_active=true", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_get_course(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/courses",
            json={"title": "Get Course"},
            headers={"Authorization": f"Bearer {token}"},
        )
        course_id = resp_data(create_resp)["id"]
        resp = await client.get(f"/api/v1/courses/{course_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp_data(resp)["title"] == "Get Course"

    async def test_update_course(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/courses",
            json={"title": "Old Title"},
            headers={"Authorization": f"Bearer {token}"},
        )
        course_id = resp_data(create_resp)["id"]
        resp = await client.patch(
            f"/api/v1/courses/{course_id}",
            json={"title": "New Title", "price": 199.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["title"] == "New Title"

    async def test_delete_course(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/courses",
            json={"title": "Delete Me"},
            headers={"Authorization": f"Bearer {token}"},
        )
        course_id = resp_data(create_resp)["id"]
        resp = await client.delete(f"/api/v1/courses/{course_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

    async def test_learner_cannot_create_course(self, client, db):
        await make_user(db, UserRole.learner, username="crs_learner")
        token = await get_token(client, "crs_learner")
        resp = await client.post(
            "/api/v1/courses",
            json={"title": "Forbidden"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_get_nonexistent_course_returns_404(self, client, db):
        import uuid
        token = await _admin_token(client, db)
        resp = await client.get(f"/api/v1/courses/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404
