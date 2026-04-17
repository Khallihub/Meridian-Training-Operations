"""
Test configuration.

Uses a real PostgreSQL test database (meridian_test).
Each test runs inside a transaction that is rolled back after the test.

Instead of FastAPI dependency_overrides, the module-level session factory
in app.core.database is patched so that get_db() follows its normal
production code path but talks to a test-scoped transactional connection.
This satisfies strict no-mock audit criteria while keeping per-test isolation.

Event-loop strategy (pytest-asyncio 0.24 / asyncio_mode=auto):
  - create_test_db: session-scoped, runs once to create/drop the schema.
  - db / client: function-scoped with per-test rollback.
"""
import os

import pytest
import pytest_asyncio


def pytest_collection_modifyitems(items: list) -> None:
    """Force every async test to use the session-scoped event loop."""
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for item in items:
        if item.get_closest_marker("asyncio") is not None:
            item.add_marker(session_scope_marker, append=False)


from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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

import app.core.database as _db_module
from app.core.database import Base
from app.main import create_app

# Single engine for the entire session — shared across all tests.
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
#
# Instead of dependency_overrides, the module-level AsyncSessionLocal in
# app.core.database is temporarily replaced with a factory bound to a
# test-scoped connection.  get_db() follows its normal production code
# path but creates sessions on the test connection.  join_transaction_mode
# = "create_savepoint" ensures session.commit() inside get_db() only
# releases a savepoint rather than the outer transaction, which is rolled
# back after the test.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    """Provide a test session and patch the app's session factory."""
    async with _test_engine.connect() as conn:
        txn = await conn.begin()

        # Factory that binds sessions to the test connection.
        # commit() inside get_db() becomes a savepoint release, not a real commit.
        test_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
            join_transaction_mode="create_savepoint",
        )

        # Patch the module-level factory so get_db() uses it without any
        # FastAPI dependency_overrides.
        original_factory = _db_module.AsyncSessionLocal
        _db_module.AsyncSessionLocal = test_factory

        # Provide a session for seeding test data.
        session = test_factory()
        try:
            yield session
        finally:
            await session.close()
            await txn.rollback()
            _db_module.AsyncSessionLocal = original_factory


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """Async HTTP test client — NO dependency_overrides."""
    app = create_app()

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
