"""API tests for locations and rooms CRUD endpoints."""

import pytest

from tests.conftest import get_token, make_user, resp_data
from app.modules.users.models import UserRole


async def _admin_token(client, db):
    await make_user(db, UserRole.admin, username="loc_admin")
    return await get_token(client, "loc_admin")


async def _auth_token(client, db):
    await make_user(db, UserRole.learner, username="loc_learner")
    return await get_token(client, "loc_learner")


@pytest.mark.asyncio
class TestLocationsCRUD:
    async def test_create_location(self, client, db):
        token = await _admin_token(client, db)
        resp = await client.post(
            "/api/v1/locations",
            json={"name": "Downtown Campus", "address": "123 Main St", "timezone": "UTC"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert data["name"] == "Downtown Campus"

    async def test_list_locations(self, client, db):
        token = await _admin_token(client, db)
        # Create a location first
        await client.post(
            "/api/v1/locations",
            json={"name": "List Site"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get("/api/v1/locations", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_location(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/locations",
            json={"name": "Get Site"},
            headers={"Authorization": f"Bearer {token}"},
        )
        loc_id = resp_data(create_resp)["id"]
        resp = await client.get(f"/api/v1/locations/{loc_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp_data(resp)["name"] == "Get Site"

    async def test_update_location(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/locations",
            json={"name": "Old Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        loc_id = resp_data(create_resp)["id"]
        resp = await client.patch(
            f"/api/v1/locations/{loc_id}",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["name"] == "New Name"

    async def test_delete_location(self, client, db):
        token = await _admin_token(client, db)
        create_resp = await client.post(
            "/api/v1/locations",
            json={"name": "To Delete"},
            headers={"Authorization": f"Bearer {token}"},
        )
        loc_id = resp_data(create_resp)["id"]
        resp = await client.delete(f"/api/v1/locations/{loc_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

    async def test_learner_cannot_create_location(self, client, db):
        token = await _auth_token(client, db)
        resp = await client.post(
            "/api/v1/locations",
            json={"name": "Forbidden Site"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestRoomsCRUD:
    async def _create_location(self, client, token):
        resp = await client.post(
            "/api/v1/locations",
            json={"name": "Room Parent Site"},
            headers={"Authorization": f"Bearer {token}"},
        )
        return resp_data(resp)["id"]

    async def test_create_room(self, client, db):
        token = await _admin_token(client, db)
        loc_id = await self._create_location(client, token)
        resp = await client.post(
            f"/api/v1/locations/{loc_id}/rooms",
            json={"name": "Room Alpha", "capacity": 25},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp_data(resp)
        assert data["name"] == "Room Alpha"
        assert data["capacity"] == 25

    async def test_list_rooms(self, client, db):
        token = await _admin_token(client, db)
        loc_id = await self._create_location(client, token)
        await client.post(
            f"/api/v1/locations/{loc_id}/rooms",
            json={"name": "Room List1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(f"/api/v1/locations/{loc_id}/rooms", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp_data(resp)
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_room(self, client, db):
        token = await _admin_token(client, db)
        loc_id = await self._create_location(client, token)
        create_resp = await client.post(
            f"/api/v1/locations/{loc_id}/rooms",
            json={"name": "Room Get1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        room_id = resp_data(create_resp)["id"]
        resp = await client.get(f"/api/v1/rooms/{room_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp_data(resp)["name"] == "Room Get1"

    async def test_update_room(self, client, db):
        token = await _admin_token(client, db)
        loc_id = await self._create_location(client, token)
        create_resp = await client.post(
            f"/api/v1/locations/{loc_id}/rooms",
            json={"name": "Room Old"},
            headers={"Authorization": f"Bearer {token}"},
        )
        room_id = resp_data(create_resp)["id"]
        resp = await client.patch(
            f"/api/v1/rooms/{room_id}",
            json={"name": "Room Updated", "capacity": 50},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp_data(resp)["name"] == "Room Updated"

    async def test_delete_room(self, client, db):
        token = await _admin_token(client, db)
        loc_id = await self._create_location(client, token)
        create_resp = await client.post(
            f"/api/v1/locations/{loc_id}/rooms",
            json={"name": "Room Del"},
            headers={"Authorization": f"Bearer {token}"},
        )
        room_id = resp_data(create_resp)["id"]
        resp = await client.delete(f"/api/v1/rooms/{room_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204
