"""
Pydantic contracts for outgoing API responses.
"""
from pydantic import BaseModel
from typing import Any, List, Optional, Dict


class PredictResponseSchema(BaseModel):
    """
    Schema for a successful prediction result.
    """
    request_id: str
    prediction: Any
    probability: Optional[float]
    model_id: str
    model_version: str
    latency_ms: float
    warnings: List[str]
    explanation: Optional[Dict[str, Any]] = None


class HealthResponseSchema(BaseModel):
    """
    Schema for the health check probe.
    """
    status: str
    version: str


class ModelAliasSchema(BaseModel):
    alias: str
    model_id: str
    version: str


class ModelsResponseSchema(BaseModel):
    """
    Schema for listing active inference models.
    """
    aliases: List[ModelAliasSchema]


class VersionResponseSchema(BaseModel):
    """
    Schema for version reporting.
    """
    platform_version: str
    api_version: str


class RedisHealthResponseSchema(BaseModel):
    """
    Schema for the Redis Cloud health check probe.
    """
    connection_status: str
    ping_latency_ms: float
    redis_version: str
    memory_usage: Any
    connected_clients: int
    url_redacted: Optional[str] = None
