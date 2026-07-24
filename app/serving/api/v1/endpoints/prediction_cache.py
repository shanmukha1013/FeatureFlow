"""
Implements the Prediction Cache API endpoints (`Phase 4`).
"""
from fastapi import APIRouter, status, HTTPException, Query
from typing import Optional
from app.serving.schemas.prediction_cache import (
    PredictionCacheGetResponseSchema,
    PredictionCacheRefreshResponseSchema,
    PredictionCacheDeleteResponseSchema,
    PredictionCacheStatsSchema
)
from app.cache.prediction_cache import get_prediction_cache

router = APIRouter()


@router.get("/predictions/cache", response_model=PredictionCacheGetResponseSchema, status_code=status.HTTP_200_OK)
async def get_prediction_cache_status():
    """Returns Prediction Cache status and live statistics (`Requirement 7`)."""
    cache = await get_prediction_cache()
    stats = await cache.get_stats()
    return PredictionCacheGetResponseSchema(
        status="success",
        statistics=PredictionCacheStatsSchema(**stats)
    )


@router.get("/predictions/cache/statistics", response_model=PredictionCacheGetResponseSchema, status_code=status.HTTP_200_OK)
async def get_prediction_cache_statistics():
    """Returns detailed telemetry statistics for the Prediction Cache (`Requirement 6 & 7`)."""
    cache = await get_prediction_cache()
    stats = await cache.get_stats()
    return PredictionCacheGetResponseSchema(
        status="success",
        statistics=PredictionCacheStatsSchema(**stats)
    )


@router.post("/predictions/cache/refresh", response_model=PredictionCacheRefreshResponseSchema, status_code=status.HTTP_200_OK)
async def refresh_prediction_cache_endpoint():
    """Forces a cache warm-up and resynchronization (`Requirement 7 & 9`)."""
    cache = await get_prediction_cache()
    res = await cache.warm_cache()
    if res.get("status") != "success":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=res.get("error", "Failed to warm cache."))
    return PredictionCacheRefreshResponseSchema(
        status="success",
        message="Prediction Cache warmed up and synchronized successfully.",
        warmed_champions=res.get("warmed_champions", 0),
        warmed_models=res.get("warmed_models", 0),
        timestamp=res.get("timestamp", "")
    )


@router.delete("/predictions/cache", response_model=PredictionCacheDeleteResponseSchema, status_code=status.HTTP_200_OK)
async def clear_prediction_cache_endpoint(
    model_id: Optional[str] = Query(None, description="Optional model ID filter"),
    dataset: Optional[str] = Query(None, description="Optional dataset filter")
):
    """Evicts prediction cache entries (`Requirement 7`). If no query parameters given, evicts all prediction entries."""
    cache = await get_prediction_cache()
    deleted = await cache.invalidate_cache(model_id=model_id, dataset=dataset)
    return PredictionCacheDeleteResponseSchema(
        status="success",
        deleted=deleted,
        target=f"model:{model_id}" if model_id else (f"dataset:{dataset}" if dataset else "all")
    )


@router.delete("/predictions/cache/{key}", response_model=PredictionCacheDeleteResponseSchema, status_code=status.HTTP_200_OK)
async def delete_prediction_cache_key_endpoint(key: str):
    """Evicts a specific prediction cache key (`Requirement 7`)."""
    cache = await get_prediction_cache()
    deleted = await cache.invalidate_cache(key=key)
    return PredictionCacheDeleteResponseSchema(
        status="success",
        deleted=deleted,
        target=key
    )
