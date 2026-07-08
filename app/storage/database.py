import sys
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Verify database_url is present, otherwise app/config.py should have already exited.
if not settings.database_url:
    logger.error("DATABASE_URL is not set. Exiting.")
    sys.exit(1)

# Create the async SQLAlchemy engine
# pool_pre_ping enables connection verification on checkout (handles reconnects gracefully)
try:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
except Exception as e:
    logger.exception(f"Failed to initialize database engine: {e}")
    sys.exit(1)

# Create a configured "Session" class
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Declarative base for models
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI that yields an async database session.
    Closes the session automatically when the request finishes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    Creates all tables. To be called on application startup.
    """
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            # Note: This does not handle migrations, use Alembic in production
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Successfully initialized database tables.")
    except Exception as e:
        logger.exception(f"Database connection or table creation failed: {e}")
        raise
