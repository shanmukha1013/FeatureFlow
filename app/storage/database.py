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
# When running under pytest, NullPool ensures database connections are never
# cached or shared across event loops.
try:
    import os
    if "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST") or settings.environment.lower() == "test":
        from sqlalchemy.pool import NullPool
        engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
            poolclass=NullPool,
        )
    else:
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
    Creates all tables and seeds default roles, permissions, and admin user.
    """
    try:
        # Import models so they are registered with Base.metadata before creating tables
        from app.storage.models import Role, Permission, RolePermission, User
        from app.security.auth import get_password_hash
        from sqlalchemy.future import select

        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Successfully initialized database tables.")

        # Seed RBAC and Admin
        async with AsyncSessionLocal() as session:
            # Roles
            admin_role = await session.execute(select(Role).filter_by(name="ADMIN"))
            admin_role = admin_role.scalar_one_or_none()
            if not admin_role:
                admin_role = Role(name="ADMIN", description="Superuser")
                ml_role = Role(name="ML_ENGINEER", description="Can manage ML pipelines")
                ds_role = Role(name="DATA_SCIENTIST", description="Can run experiments")
                viewer_role = Role(name="VIEWER", description="Read-only access")
                session.add_all([admin_role, ml_role, ds_role, viewer_role])
                await session.flush()

                # We can seed specific permissions later if needed, but ADMIN gets a * wildcard for now
                admin_perm = Permission(action="*", resource="*", description="Full Access")
                session.add(admin_perm)
                await session.flush()

                session.add(RolePermission(role_id=admin_role.id, permission_id=admin_perm.id))

                # Admin user
                admin_user = User(
                    username="admin",
                    email=settings.default_admin_email,
                    hashed_password=get_password_hash(settings.default_admin_password),
                    role_id=admin_role.id,
                    status="ACTIVE"
                )
                session.add(admin_user)
                await session.commit()
                logger.info("Seeded default roles and admin user.")

    except Exception as e:
        logger.exception(f"Database connection or table creation failed: {e}")
        raise
