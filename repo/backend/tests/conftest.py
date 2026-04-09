"""
Test configuration.

Uses a real PostgreSQL test database (meridian_test).
Each test runs in a transaction that is rolled back after the test.
"""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Override DB URL to use test DB before any app imports
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://meridian:meridian@localhost:5432/meridian_test",
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

# Test engine
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_db():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db():
    """Each test gets a session that is rolled back after the test."""
    async with test_engine.begin() as conn:
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
    resp = await client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
