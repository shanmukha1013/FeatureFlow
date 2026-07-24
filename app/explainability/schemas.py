from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime


class FeatureImportance(BaseModel):
    feature: str
    importance: float
    direction: str  # 'positive' or 'negative'


class ExplanationResponse(BaseModel):
    prediction_id: str
    model_id: str
    generation_time_ms: float
    execution_time: datetime
    cache_status: str
    top_features: List[FeatureImportance]
    visualization_data: Dict[str, Any]
    explanation_version: Optional[str] = None
    model_version: Optional[str] = None
    feature_version: Optional[str] = None
    dataset_version: Optional[str] = None
    shap_library_version: Optional[str] = None


class GlobalFeatureImportance(BaseModel):
    feature: str
    mean_absolute_shap: float


class GlobalExplanationResponse(BaseModel):
    model_id: str
    dataset_id: Optional[str]
    model_version: Optional[str]
    global_feature_importance: List[GlobalFeatureImportance]
    top_n_features: List[str]
    created_at: datetime


class CacheStatisticsResponse(BaseModel):
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_ratio: float
    average_latency_ms: float
    total_memory_usage_mb: float


class ExplanationStatisticsResponse(BaseModel):
    total_explanations_generated: int
    average_generation_time_ms: float
    cache_hit_rate: float
    total_cache_hits: int
    total_cache_misses: int


class GenerateExplanationRequest(BaseModel):
    prediction_id: str
    model_alias: str = "default"
    features: Dict[str, Any]
