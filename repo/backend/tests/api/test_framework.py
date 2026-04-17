"""API tests for framework endpoints: docs, redoc, openapi.json."""

import pytest


@pytest.mark.asyncio
class TestFrameworkEndpoints:
    async def test_docs_endpoint(self, client, db):
        resp = await client.get("/api/v1/docs")
        assert resp.status_code == 200

    async def test_redoc_endpoint(self, client, db):
        resp = await client.get("/api/v1/redoc")
        assert resp.status_code == 200

    async def test_openapi_json(self, client, db):
        resp = await client.get("/api/v1/openapi.json")
        assert resp.status_code == 200
        body = resp.json()
        # May be envelope-wrapped or raw
        data = body.get("data", body) if isinstance(body, dict) else body
        assert "openapi" in data or "components" in data
        assert "paths" in data or "components" in data
