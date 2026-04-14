"""
Test configuration.

Uses a real PostgreSQL test database (meridian_test).
Each test runs in a transaction that is rolled back after the test.

Event-loop strategy (pytest-asyncio 0.24 / asyncio_mode=auto):
  - create_test_db: session-scoped, runs once to create/drop the schema.
  - db / client: function-scoped; each call creates a fresh AsyncEngine on
    the current event loop so asyncpg connections are never shared across
    different loops.  This is slower than sharing a pool but avoids the
    "Future attached to a different loop" error that arises when a
    session-loop engine is used from a function-loop test coroutine.
"""
import os

import pytest
import pytest_asyncio


def pytest_collection_modifyitems(items: list) -> None:
    """Force every async test to use the session-scoped event loop.

    Without this, pytest-asyncio 0.24 assigns a function-scoped loop to each
    test while fixtures default to session scope (asyncio_default_fixture_loop_scope
    = "session"), causing asyncpg Futures to be "attached to a different loop".
    Running everything on the one session loop avoids that entirely.
    """
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for item in items:
        if item.get_closest_marker("asyncio") is not None:
            item.add_marker(session_scope_marker, append=False)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Override DB URL to use test DB before any app imports
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://meridian:meridian@db:5432/meridian_test",
)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long-here")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "")
os.environ.setdefault("PAYMENT_SIGNATURE_SECRET", "test-payment-secret")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/14")

from app.core.database import Base, get_db
from app.main import create_app

# Single engine for the entire session — all tests and fixtures share the same
# asyncpg connection pool on the session event loop, avoiding loop-mismatch errors.
_test_engine = create_async_engine(TEST_DB_URL, echo=False)


# ---------------------------------------------------------------------------
# Schema setup — session-scoped, runs once on the session event loop
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def create_test_db():
    """Create all tables once per test session, then drop them on teardown."""
    async with _test_engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


# ---------------------------------------------------------------------------
# Per-test DB session — each test gets a rolled-back transaction
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    """Each test gets a session wrapped in a transaction that is rolled back."""
    async with _test_engine.begin() as conn:
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
            await conn.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """Async HTTP test client with overridden DB session."""
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

from app.core.security import hash_password
from app.modules.users.models import User, UserRole


async def make_user(db: AsyncSession, role: UserRole = UserRole.learner, username: str | None = None) -> User:
    import uuid
    u = User(
        username=username or f"user_{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("TestPass@1234"),
        role=role,
        is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


async def get_token(client: AsyncClient, username: str, password: str = "TestPass@1234") -> str:
    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp_data(resp)["access_token"]


def resp_data(resp) -> dict:
    """Unwrap the standard PRD response envelope and return the data payload.
    For error responses, returns the error sub-object.
    Falls back to the raw JSON body if not in envelope format.
    """
    body = resp.json()
    if isinstance(body, dict) and "data" in body and "meta" in body:
        if resp.status_code < 400:
            return body["data"] if body["data"] is not None else {}
        # Error envelope: return the error dict for test assertions
        return body.get("error") or {}
    return body
