"""
FeatureFlow Cache Module.

Provides a production-grade distributed cache and online feature store backed by Redis Cloud.
Ensures zero-crash resilience: if Redis is unavailable or times out, all operations gracefully
fall back to PostgreSQL as the system of record.
"""
from app.cache.redis_client import RedisClient, get_redis_client
from app.cache.cache_manager import CacheManager, get_cache_manager
from app.cache.online_store import OnlineFeatureStore, get_online_store

__all__ = [
    "RedisClient",
    "get_redis_client",
    "CacheManager",
    "get_cache_manager",
    "OnlineFeatureStore",
    "get_online_store",
]

