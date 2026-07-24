"""
Prediction Cache API schemas (`Phase 4`).
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PredictionCacheStatsSchema(BaseModel):
    """Telemetry metrics for the Prediction Cache."""
    prediction_cache_hits: int = Field(0, description="Total number of prediction cache hits")
    prediction_cache_misses: int = Field(0, description="Total number of prediction cache misses")
    hit_ratio: float = Field(0.0, description="Percentage of requests served from cache (0-100)")
    avg_lookup_latency_ms: float = Field(0.0, description="Average time in milliseconds spent checking cache")
    avg_prediction_latency_ms: float = Field(0.0, description="Average time in milliseconds spent computing predictions")
    redis_lookup_time_ms: float = Field(0.0, description="Average Redis roundtrip time in milliseconds")
    postgresql_fallback_count: int = Field(0, description="Number of times prediction engine fell back due to cache/store miss")
    cache_size: int = Field(0, description="Number of active prediction keys (`pred:*`) in Redis")
    memory_usage: Dict[str, Any] = Field(default_factory=dict, description="Live Redis memory usage telemetry")
    expired_entries: int = Field(0, description="Number of expired cache entries")
    evicted_entries: int = Field(0, description="Number of evicted or invalidated cache entries")
    last_refresh: Optional[str] = Field(None, description="ISO timestamp of last cache operation or refresh")


class PredictionCacheGetResponseSchema(BaseModel):
    """Response schema for GET /api/v1/predictions/cache and /statistics."""
    status: str = Field("success")
    statistics: PredictionCacheStatsSchema


class PredictionCacheRefreshResponseSchema(BaseModel):
    """Response schema for POST /api/v1/predictions/cache/refresh."""
    status: str = Field("success")
    message: str
    warmed_champions: int = Field(0)
    warmed_models: int = Field(0)
    timestamp: str


class PredictionCacheDeleteResponseSchema(BaseModel):
    """Response schema for DELETE /api/v1/predictions/cache and /{key}."""
    status: str = Field("success")
    deleted: int = Field(0, description="Number of keys evicted")
    target: Optional[str] = Field(None, description="Target key, model_id, or 'all'")
