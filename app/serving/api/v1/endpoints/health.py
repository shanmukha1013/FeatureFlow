"""
Implements the health check endpoint for Kubernetes liveness/readiness probes.
"""
from fastapi import APIRouter, Depends

from app.cache import get_cache_manager
from app.serving.config import serving_config
from app.serving.dependencies import get_prediction_engine
from app.serving.schemas.response import HealthResponseSchema, RedisHealthResponseSchema

router = APIRouter()


@router.get("/live")
def liveness_probe():
    """
    Verifies that the API server process is alive.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(engine=Depends(get_prediction_engine)):
    """
    Verifies that the API server is ready to receive requests.
    Checks PostgreSQL, Redis, and MLflow connectivity.
    """
    import mlflow
    from fastapi.responses import JSONResponse
    from sqlalchemy import text

    from app.cache import RedisClient
    from app.storage.database import AsyncSessionLocal

    is_ready = True
    reasons = []

    if engine is None:
        is_ready = False
        reasons.append("Inference registry not initialized")

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        is_ready = False
        reasons.append("PostgreSQL unreachable")

    redis_client = await RedisClient.get_instance()
    if not redis_client.is_connected:
        is_ready = False
        reasons.append("Redis unreachable")

    try:
        mlflow.get_tracking_uri()
    except Exception:
        is_ready = False
        reasons.append("MLflow unconfigured")

    if not is_ready:
        return JSONResponse(status_code=503, content={"status": "unready", "reasons": reasons})

    return {"status": "ready"}


@router.get("/health", response_model=HealthResponseSchema)
def health_check(engine=Depends(get_prediction_engine)):
    """
    Comprehensive health check of all components.
    """
    if engine is None:
        raise Exception("Fatal Error: Inference registry is not initialized.")

    return HealthResponseSchema(
        status="healthy",
        version=serving_config.platform_version
    )


@router.get("/health/redis", response_model=RedisHealthResponseSchema)
async def redis_health_check():
    """
    Returns Redis Cloud connection status, ping latency, version, memory usage, and connected clients.
    """
    cache = get_cache_manager()
    health_data = await cache.health()
    return RedisHealthResponseSchema(**health_data)
