"""
Implements the health check endpoint for Kubernetes liveness/readiness probes.
"""
from fastapi import APIRouter, Depends
from app.serving.schemas.response import HealthResponseSchema, RedisHealthResponseSchema
from app.serving.config import serving_config
from app.serving.dependencies import get_prediction_engine
from app.cache import get_cache_manager

router = APIRouter()


@router.get("/health", response_model=HealthResponseSchema)
def health_check(engine=Depends(get_prediction_engine)):
    """
    Verifies that the API server is alive and the core inference engine is initialized.
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
