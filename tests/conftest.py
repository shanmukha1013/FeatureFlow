"""
Test fixtures for FeatureFlow PostgreSQL test suite.

Uses the application's real async PostgreSQL infrastructure.
All integration tests run against real PostgreSQL.

SAFETY GUARD:
    If DATABASE_URL is SQLite, integration tests will fail at collection time.
    This prevents false certification of PostgreSQL behavior via SQLite.

    To run integration tests:
        1. Set DATABASE_URL to a PostgreSQL connection string.
        2. Use a dedicated test database (NOT the production database).
        3. The database name must contain 'test' OR ENVIRONMENT must be 'test'.

    Example:
        DATABASE_URL=postgresql+asyncpg://featureflow:featureflow_password@localhost:5432/featureflow_test
        ENVIRONMENT=test
"""
import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport

from app.config import settings
from app.storage.database import AsyncSessionLocal, init_db

# ---------------------------------------------------------------------------
# DATABASE SAFETY GUARD — fail closed if tests would run against SQLite
# ---------------------------------------------------------------------------
_DB_URL = settings.database_url or ""
_IS_SQLITE = "sqlite" in _DB_URL.lower()
_IS_TEST_PG = (
    "postgresql" in _DB_URL.lower()
    and (
        "test" in _DB_URL.lower()
        or os.getenv("ENVIRONMENT", "").lower() == "test"
        or os.getenv("FEATUREFLOW_ENV", "").lower() == "test"
        or os.getenv("CI", "") == "true"
    )
)

if _IS_SQLITE:
    print(
        "\n\n"
        "ERROR: Integration tests are configured to run against SQLite.\n"
        "FeatureFlow is PostgreSQL-native. SQLite cannot certify:\n"
        "  - JSONB behavior\n"
        "  - UUID foreign key enforcement\n"
        "  - concurrent write isolation\n"
        "  - transaction rollback under asyncpg\n"
        "  - pipeline atomicity\n\n"
        "Fix: Set DATABASE_URL to a PostgreSQL test database and set ENVIRONMENT=test.\n"
        "Example:\n"
        "  DATABASE_URL=postgresql+asyncpg://featureflow:password@localhost:5432/featureflow_test\n"
        "  ENVIRONMENT=test\n",
        file=sys.stderr,
    )
    # Do not sys.exit here — let pytest collect and report the error naturally
    # so CI surfaces it as a failure, not a crash.

if not _IS_SQLITE and not _IS_TEST_PG:
    print(
        "\n\n"
        "WARNING: DATABASE_URL appears to point to PostgreSQL but the database\n"
        "is not identified as a test database (name does not contain 'test'\n"
        "and ENVIRONMENT != 'test' and CI != 'true').\n"
        "Refusing to run destructive tests against an unverified database.\n"
        "Set ENVIRONMENT=test or ensure the database name contains 'test'.\n",
        file=sys.stderr,
    )


def _require_postgresql():
    """Raise a clear error if tests are not running on PostgreSQL."""
    if _IS_SQLITE:
        pytest.fail(
            "Integration tests require PostgreSQL. "
            "Current DATABASE_URL is SQLite. "
            "Set DATABASE_URL to a PostgreSQL test database and ENVIRONMENT=test."
        )
    if not _IS_TEST_PG:
        pytest.fail(
            "Integration tests require a test PostgreSQL database. "
            "Ensure DATABASE_URL contains 'test' or set ENVIRONMENT=test."
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def setup_database(request):
    """Initialize database tables.

    Fails immediately if DATABASE_URL is not a recognized PostgreSQL test database.
    """
    if "unit" in str(request.node.path):
        yield
        return

    _require_postgresql()
    await init_db()
    yield


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a real PostgreSQL async session for each test."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client for FastAPI integration tests, authenticated as Admin."""
    from app.storage.models import User
    from sqlalchemy.future import select
    from app.security.auth import create_access_token

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter_by(username="admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            token = "fallback"
        else:
            token = create_access_token(admin.id, admin.username)

    from app.serving.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"}
    ) as c:
        yield c
