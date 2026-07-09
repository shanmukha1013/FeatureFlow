"""
Implements the Model Registry Cache API endpoints (`Phase 3`).
"""
from fastapi import APIRouter, status, HTTPException
from app.serving.schemas.model_cache import (
    ModelCacheGetResponseSchema,
    ModelCacheRefreshResponseSchema,
    ModelCacheDeleteResponseSchema,
    ModelCacheStatsSchema
)
from app.cache.model_cache import get_model_registry_cache

router = APIRouter()


@router.get("/models/cache", response_model=ModelCacheGetResponseSchema, status_code=status.HTTP_200_OK)
async def get_model_cache_statistics():
    """Returns real-time Model Registry cache statistics (hits, misses, refresh count, memory usage)."""
    cache = await get_model_registry_cache()
    stats = await cache.get_stats()
    return ModelCacheGetResponseSchema(
        status="success",
        statistics=ModelCacheStatsSchema(**stats)
    )


@router.post("/models/cache/refresh", response_model=ModelCacheRefreshResponseSchema, status_code=status.HTTP_200_OK)
async def refresh_model_cache_endpoint():
    """Forces a complete resynchronization of active models and champions from PostgreSQL into Redis."""
    cache = await get_model_registry_cache()
    res = await cache.refresh_all_caches()
    if res.get("status") == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=res.get("error"))
    return ModelCacheRefreshResponseSchema(
        status="success",
        message="Model registry cache refreshed successfully from PostgreSQL.",
        refreshed_models_count=res.get("refreshed_models_count", 0),
        refreshed_champions_count=res.get("refreshed_champions_count", 0),
        statistics=ModelCacheStatsSchema(**res["statistics"])
    )


@router.delete("/models/cache/{model_id}", response_model=ModelCacheDeleteResponseSchema, status_code=status.HTTP_200_OK)
async def delete_model_cache_endpoint(model_id: str):
    """Evicts a model (`model:{model_id}`, `metadata:{model_id}`) and any associated champion records from Redis."""
    cache = await get_model_registry_cache()
    deleted = await cache.delete_model_cache(model_id)
    return ModelCacheDeleteResponseSchema(
        status="success",
        deleted=deleted,
        model_id=model_id
    )
