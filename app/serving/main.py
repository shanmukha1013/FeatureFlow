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
    import threading
    from app.data.discovery import DatasetDiscovery
    from app.serving.dependencies import _prediction_engine
    from app.cache import RedisClient
    from app.cache.health_monitor import get_health_monitor
    from app.cache.recovery_manager import get_recovery_manager
    from app.monitoring.audit import AuditLogger, AuditEvent
    from app.storage.database import AsyncSessionLocal

    # Initialize Database connection and create tables
    await init_db()

    # Initialize Redis Cloud connection pool
    redis_client = await RedisClient.get_instance()

    # Phase 13A: Startup Validation
    async def validate_startup():
        from app.config import settings
        import sys
        import os
        import mlflow

        try:
            # 1. Environment variables
            if not settings.jwt_secret_keys or settings.jwt_secret_keys == "featureflow-default-dev-secret-key-32b":
                if settings.is_production:
                    print("CRITICAL: Production JWT secret key is missing or insecure.", file=sys.stderr)
                    sys.exit(1)

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

    # Start Prediction Engine immediately to warm caches
    await _prediction_engine.start()

    # Phase 5: Start Redis enterprise background services
    health_monitor = await get_health_monitor()
    await health_monitor.start()

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

    def run_discovery():
        discovery = DatasetDiscovery()
        discovery.discover_datasets()

    import sys
    import os
    from app.config import settings

    # Phase 12: Start system metrics collection in background
    metrics_task = asyncio.create_task(collect_system_metrics())

    if "pytest" not in sys.modules and not os.getenv("PYTEST_CURRENT_TEST") and settings.environment.lower() != "test":
        threading.Thread(target=run_discovery, daemon=True).start()
    yield
    # Stop background tasks
    metrics_task.cancel()
    # Phase 5: Stop background services gracefully
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

    # Register metrics endpoint
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response, Depends
    from app.config import settings
    from app.security.dependencies import get_current_user

    metrics_deps = [Depends(get_current_user)] if settings.enable_metrics_auth else []

    @app.get("/metrics", tags=["observability"], dependencies=metrics_deps)
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


# The standard ASGI entrypoint (e.g. `uvicorn app.serving.main:app`)
app = create_app()
