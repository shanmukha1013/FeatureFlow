import json
from typing import Dict, Any, Optional

from app.cache.redis_client import RedisClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataQualityCacheManager:
    """
    Manages Redis caching for Data Quality Health Scores and Validation Summaries.
    Ensures rapid retrieval for dashboard APIs.
    """
    def __init__(self):
        self.redis = RedisClient()

    def _build_health_key(self, dataset_name: str) -> str:
        return f"ff:dq:health:{dataset_name}"

    def _build_summary_key(self, dataset_version_id: str) -> str:
        return f"ff:dq:summary:{dataset_version_id}"

    async def cache_health_score(self, dataset_name: str, health_score: float, ttl: int = 3600):
        """Caches the latest health score for a dataset."""
        key = self._build_health_key(dataset_name)
        try:
            if self.redis.client:
                await self.redis.client.set(key, str(health_score), ex=ttl)
        except Exception as e:
            logger.warning(f"Failed to cache dataset health score: {e}")

    async def get_health_score(self, dataset_name: str) -> Optional[float]:
        """Retrieves cached health score."""
        key = self._build_health_key(dataset_name)
        try:
            if self.redis.client:
                val = await self.redis.client.get(key)
                return float(val) if val else None
            return None
        except Exception:
            return None

    async def cache_validation_summary(self, dataset_version_id: str, summary_data: Dict[str, Any], ttl: int = 86400):
        """Caches validation summary. Typically lives longer (1 day)."""
        key = self._build_summary_key(dataset_version_id)
        try:
            if self.redis.client:
                await self.redis.client.set(key, json.dumps(summary_data), ex=ttl)
        except Exception as e:
            logger.warning(f"Failed to cache validation summary: {e}")

    async def get_validation_summary(self, dataset_version_id: str) -> Optional[Dict[str, Any]]:
        key = self._build_summary_key(dataset_version_id)
        try:
            if self.redis.client:
                val = await self.redis.client.get(key)
                return json.loads(val) if val else None
            return None
        except Exception:
            return None

    async def invalidate_dataset(self, dataset_name: str, dataset_version_id: str):
        """Invalidate cache when a new validation or version occurs."""
        try:
            if self.redis.client:
                await self.redis.client.delete(self._build_health_key(dataset_name))
                await self.redis.client.delete(self._build_summary_key(dataset_version_id))
        except Exception:
            pass
