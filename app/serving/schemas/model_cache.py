"""
Pydantic contracts for Phase 3 Redis Model Registry Cache endpoints.
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional


class ModelCacheStatsSchema(BaseModel):
    hits: int
    misses: int
    refresh_count: int
    last_refresh: Optional[str] = None
    memory_usage_bytes: int


class ModelCacheGetResponseSchema(BaseModel):
    status: str
    statistics: ModelCacheStatsSchema


class ModelCacheRefreshResponseSchema(BaseModel):
    status: str
    message: Optional[str] = None
    refreshed_models_count: int = 0
    refreshed_champions_count: int = 0
    statistics: ModelCacheStatsSchema
    error: Optional[str] = None


class ModelCacheDeleteResponseSchema(BaseModel):
    status: str
    deleted: bool
    model_id: str
