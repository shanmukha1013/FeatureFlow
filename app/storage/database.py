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
        pool_pre_ping=True,      # verify connections before checkout
        pool_size=20,            # handle more concurrent requests
        max_overflow=40,         # allow spikes in connections
        pool_timeout=30,         # wait up to 30s before giving up
        pool_recycle=1800,       # recycle connections older than 30 mins
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
    from sqlalchemy.exc import IntegrityError, OperationalError
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Database Integrity Violation during request: {e}")
            raise
        except OperationalError as e:
            await session.rollback()
            logger.error(f"Database Operational Error (e.g. timeout, connection loss): {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected database transaction failure: {e}")
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
