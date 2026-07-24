"""
FeatureFlow Cache Module.

Provides a production-grade distributed cache and online feature store backed by Redis Cloud.
Ensures zero-crash resilience: if Redis is unavailable or times out, all operations gracefully
fall back to PostgreSQL as the system of record.
"""
from app.cache.redis_client import RedisClient, get_redis_client
from app.cache.cache_manager import CacheManager, get_cache_manager
from app.cache.online_store import OnlineFeatureStore, get_online_store
from app.cache.model_cache import ModelRegistryCache, get_model_registry_cache
from app.cache.prediction_cache import PredictionCache, get_prediction_cache
from app.cache.health_monitor import RedisHealthMonitor, get_health_monitor
from app.cache.recovery_manager import RedisRecoveryManager, get_recovery_manager
from app.cache.performance_benchmark import RedisBenchmark, get_benchmark

__all__ = [
    "RedisClient",
    "get_redis_client",
    "CacheManager",
    "get_cache_manager",
    "OnlineFeatureStore",
    "get_online_store",
    "ModelRegistryCache",
    "get_model_registry_cache",
    "PredictionCache",
    "get_prediction_cache",
    "RedisHealthMonitor",
    "get_health_monitor",
    "RedisRecoveryManager",
    "get_recovery_manager",
    "RedisBenchmark",
    "get_benchmark",
]
