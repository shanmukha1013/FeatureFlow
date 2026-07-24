"""
CacheManager module for FeatureFlow.

Provides high-level distributed caching and online feature store capabilities.
Guarantees zero-crash execution by delegating to RedisClient's retry and fallback logic.
If Redis is down or unreachable, CacheManager returns None or False so that repositories
and inference engines automatically retrieve fresh data directly from PostgreSQL.
"""
import json
from typing import Optional, Dict, Any, Union, List
import redis.asyncio as aioredis

from app.cache.redis_client import RedisClient, get_redis_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    High-level cache abstraction for online feature serving and platform metadata caching.

    All operations are asynchronous and safe against network failures.
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()

    async def get(self, key: str) -> Optional[str]:
        """Retrieves a string value from cache by key. Returns None on cache miss or connection failure."""
        async def _op(client: aioredis.Redis) -> Optional[str]:
            return await client.get(key)

        res = await self.redis.execute_with_retry(_op)
        return str(res) if res is not None else None

    async def set(self, key: str, value: Union[str, int, float], ttl: Optional[int] = 3600) -> bool:
        """Stores a string/primitive value in cache with optional TTL in seconds."""
        async def _op(client: aioredis.Redis) -> bool:
            if ttl and ttl > 0:
                res = await client.set(name=key, value=str(value), ex=ttl)
            else:
                res = await client.set(name=key, value=str(value))
            return bool(res)

        res = await self.redis.execute_with_retry(_op)
        return bool(res)

    async def delete(self, *keys: str) -> bool:
        """Deletes one or more keys from cache. Returns True if at least one key was deleted."""
        if not keys:
            return False

        async def _op(client: aioredis.Redis) -> int:
            return await client.delete(*keys)

        res = await self.redis.execute_with_retry(_op)
        return bool(res and res > 0)

    async def exists(self, key: str) -> bool:
        """Checks whether a key exists in cache."""
        async def _op(client: aioredis.Redis) -> int:
            return await client.exists(key)

        res = await self.redis.execute_with_retry(_op)
        return bool(res and res > 0)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves and deserializes a JSON object from cache."""
        raw = await self.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Failed to decode JSON from cache key '{key}': {e}")
            return None

    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = 3600) -> bool:
        """Serializes and stores a dictionary/object as JSON in cache."""
        try:
            serialized = json.dumps(value, default=str)
            return await self.set(key=key, value=serialized, ttl=ttl)
        except Exception as e:
            logger.warning(f"Failed to serialize JSON for cache key '{key}': {e}")
            return False

    async def get_multi(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Batch retrieval of multiple keys. Missing or failed items map to None."""
        if not keys:
            return {}

        async def _op(client: aioredis.Redis) -> List[Optional[str]]:
            return await client.mget(keys)

        res = await self.redis.execute_with_retry(_op)
        if not res or not isinstance(res, list):
            return {k: None for k in keys}

        return {k: (str(v) if v is not None else None) for k, v in zip(keys, res)}

    async def health(self) -> Dict[str, Any]:
        """Returns diagnostic status of the underlying Redis connection."""
        return await self.redis.health_check()


def get_cache_manager() -> CacheManager:
    """Returns the singleton instance of CacheManager for dependency injection."""
    return CacheManager()
