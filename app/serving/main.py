import sys

# Prevent Evidently/Litestar from crashing when python-multipart is used instead of multipart.
# Litestar expects Marcel Hellkamp's 'multipart' package which provides MultipartSegment.
# python-multipart (by Andrew Dunham) provides the 'multipart' namespace but lacks this class.
# Since we only use python-multipart for FastAPI, we inject a dummy class to satisfy Litestar.
try:
    import multipart
    if not hasattr(multipart, "MultipartSegment"):
        multipart.MultipartSegment = type("MultipartSegment", (), {})
    if not hasattr(multipart, "ParserError"):
        multipart.ParserError = type("ParserError", (Exception,), {})
    if not hasattr(multipart, "ParserLimitReached"):
        multipart.ParserLimitReached = type("ParserLimitReached", (Exception,), {})
    if not hasattr(multipart, "MultipartParser"):
        multipart.MultipartParser = type("MultipartParser", (), {})
    if not hasattr(multipart, "parse_options_header"):
        multipart.parse_options_header = lambda *args, **kwargs: (b"", {})
except ImportError:
    pass

import sys
if "litestar" not in sys.modules:
    from unittest.mock import MagicMock
    class DummyMock(MagicMock):
        pass
    mock_litestar = DummyMock()
    sys.modules["litestar"] = mock_litestar
    sys.modules["litestar.params"] = mock_litestar
    sys.modules["litestar.exceptions"] = mock_litestar
    sys.modules["litestar.di"] = mock_litestar
    sys.modules["litestar.app"] = mock_litestar
    sys.modules["litestar._asgi"] = mock_litestar
    sys.modules["litestar.types"] = mock_litestar

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from app.serving.config import serving_config
from app.serving.api.v1.router import v1_router
from app.monitoring.middleware import monitoring_middleware
from app.serving.exceptions import (
    validation_error_handler,
    not_found_error_handler,
    service_unavailable_handler,
    internal_error_handler
)
from app.inference.exceptions import InputValidationError, ModelLoadError, InferenceError, PredictionError
from app.observability.middleware import ObservabilityMiddleware
from app.observability.instrumentation import collect_system_metrics

from contextlib import asynccontextmanager
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.storage.database import init_db
    from app.cache import RedisClient
    from app.cache.health_monitor import get_health_monitor
    from app.events.bus import EventBus
    from app.events import set_event_bus
    from app.cache.recovery_manager import get_recovery_manager
    from app.monitoring.audit import AuditLogger, AuditEvent
    from app.storage.database import AsyncSessionLocal

    # Initialize Database connection and create tables
    await init_db()

    # Initialize Redis Cloud connection pool
    redis_client = await RedisClient.get_instance()

    # Phase 13A: Startup Validation
    async def validate_startup():
        import sys
        import os
        import mlflow
        from app.config import settings

        try:
            # 1. Environment variables (No longer requires JWT)

            # 2. PostgreSQL
            try:
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import text
                    await session.execute(text("SELECT 1"))
            except Exception as e:
                print(f"CRITICAL: Failed to connect to PostgreSQL: {e}", file=sys.stderr)
                sys.exit(1)

            # 3. Redis
            if not redis_client.is_connected:
                print("CRITICAL: Failed to connect to Redis.", file=sys.stderr)
                sys.exit(1)

            # 4. MLflow
            try:
                mlflow.get_tracking_uri()
            except Exception as e:
                print(f"CRITICAL: MLflow configuration invalid: {e}", file=sys.stderr)
                sys.exit(1)

            # 5. Required directories & writable storage
            required_dirs = [settings.data_dir, "models", "reports"]
            for d in required_dirs:
                os.makedirs(d, exist_ok=True)
                if not os.access(d, os.W_OK):
                    print(f"CRITICAL: Directory {d} is not writable.", file=sys.stderr)
                    sys.exit(1)

        except SystemExit:
            raise
        except Exception as e:
            if settings.environment != "development":
                print(f"CRITICAL: Startup validation failed: {e}", file=sys.stderr)
                sys.exit(1)
            else:
                raise e

    await validate_startup()

    # Note: ML Model loading (_prediction_engine.start) has been removed from startup.
    # Phase 5: Initialize Redis Subsystem
    # In V3, Redis also powers our core EventBus
    try:
        redis_client = RedisClient()
        await redis_client.connect()
        app.state.redis = redis_client
        
        # Initialize EventBus
        event_bus = EventBus(redis_client)
        set_event_bus(event_bus)
        await event_bus.start()
        from app.services.lifecycle import LifecycleOrchestrator
        lifecycle_orchestrator = LifecycleOrchestrator(event_bus)
        app.state.lifecycle = lifecycle_orchestrator
        
        from app.features.sync_worker import OnlineStoreSyncWorker
        sync_worker = OnlineStoreSyncWorker(event_bus)
        app.state.sync_worker = sync_worker
        
        health_monitor = await get_health_monitor()
        await health_monitor.start()
    except Exception as e:
        import sys
        print(f"CRITICAL: Failed to initialize Redis subsystem: {e}", file=sys.stderr)
        sys.exit(1)

    recovery_manager = await get_recovery_manager()
    await recovery_manager.start()

    # Emit REDIS_CONNECTED audit event
    try:
        async with AsyncSessionLocal() as session:
            await AuditLogger.record(session, AuditEvent(
                event_name="REDIS_CONNECTED",
                component="FastAPI.Lifespan",
                severity="INFO",
                payload={"pool_size": redis_client.pool_size, "connected": redis_client.is_connected}
            ))
            await session.commit()
    except Exception:
        pass

    # Phase 12: Start system metrics collection in background
    metrics_task = asyncio.create_task(collect_system_metrics())

    # Note: Dataset discovery (run_discovery) has been removed from startup
    # to dramatically reduce memory footprint on Render Free tier (512MB RAM).
    # Heavy tasks like profiling should be triggered via API, not on boot.

    yield
    # Stop background tasks
    metrics_task.cancel()
    # Phase 5: Stop background services gracefully
    from app.events import get_event_bus
    
    event_bus = get_event_bus()
    if event_bus:
        await event_bus.stop()
        
    await health_monitor.stop()
    await recovery_manager.stop()

    # Emit REDIS_DISCONNECTED audit event
    try:
        async with AsyncSessionLocal() as session:
            await AuditLogger.record(session, AuditEvent(
                event_name="REDIS_DISCONNECTED",
                component="FastAPI.Lifespan",
                severity="INFO",
                payload={"reason": "application_shutdown"}
            ))
            await session.commit()
    except Exception:
        pass

    # Cleanly disconnect from Redis on application shutdown
    await redis_client.disconnect()


def create_app() -> FastAPI:
    """
    Constructs the FastAPI application for deployment.
    """
    app = FastAPI(
        title="FeatureFlow API",
        description="""
FeatureFlow is a production-grade ML platform for feature management, real-time inference, and observability.

### Features
- **Feature Store**: Centralized feature registry and serving.
- **Model Registry**: MLflow-backed model tracking and champion selection.
- **Real-time Inference**: Low-latency predictions with Redis caching.
- **Observability**: Prometheus metrics, Grafana dashboards, and data drift monitoring.
""",
        version="1.0.0",
        contact={
            "name": "MLOps Team",
            "url": "https://shanmukha-portfolio-six.vercel.app",
        },
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # 1. Mount Middleware
    from app.security.middleware import setup_security_middleware
    setup_security_middleware(app)
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=monitoring_middleware)

    # 2. Register Centralized Exception Handlers
    app.add_exception_handler(InputValidationError, validation_error_handler)
    app.add_exception_handler(InferenceError, not_found_error_handler)
    app.add_exception_handler(ModelLoadError, service_unavailable_handler)
    app.add_exception_handler(PredictionError, internal_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)

    # 3. Mount Routers
    app.include_router(v1_router, prefix=f"/api/{serving_config.api_version}")
    from app.serving.api.v1.endpoints import health, model_cache
    app.include_router(health.router, tags=["health"])
    app.include_router(model_cache.router, tags=["model_cache"])

    from app.serving.websockets import router as websockets_router
    app.include_router(websockets_router)

    # Register metrics endpoint
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response

    @app.get("/metrics", tags=["observability"])
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


# The standard ASGI entrypoint (e.g. `uvicorn app.serving.main:app`)
app = create_app()
