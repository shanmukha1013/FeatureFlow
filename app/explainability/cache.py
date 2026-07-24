import json
import hashlib
from typing import Dict, Any, Tuple, Optional
from app.cache.redis_client import get_redis_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExplanationCache:
    """
    Redis-backed caching layer specifically for SHAP explanations.
    """

    def __init__(self):
        self.redis = get_redis_client()
        self.ttl = 86400 * 7  # 7 days
        self.prefix = "shap"

    def compute_hash(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def build_key(self, model_id: str, m_ver: str, f_ver: str, payload_hash: str) -> str:
        return f"{self.prefix}:{model_id}:{m_ver}:{f_ver}:{payload_hash}"

    async def get_explanation(self, model_id: str, m_ver: str, f_ver: str, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
        if not self.redis.client:
            return None, "redis_offline"

        phash = self.compute_hash(payload)
        key = self.build_key(model_id, m_ver, f_ver, phash)

        try:
            val = await self.redis.client.get(key)
            if val:
                return json.loads(val), "redis"
            return None, "redis"
        except Exception as e:
            logger.warning(f"Failed to fetch explanation from cache: {e}")
            return None, "error"

    async def store_explanation(self, model_id: str, m_ver: str, f_ver: str, payload: Dict[str, Any], expl_data: Dict[str, Any]) -> bool:
        if not self.redis.client:
            return False

        phash = self.compute_hash(payload)
        key = self.build_key(model_id, m_ver, f_ver, phash)

        try:
            await self.redis.client.set(key, json.dumps(expl_data), ex=self.ttl)
            return True
        except Exception as e:
            logger.warning(f"Failed to store explanation in cache: {e}")
            return False


_instance = None


def get_explanation_cache() -> ExplanationCache:
    global _instance
    if _instance is None:
        _instance = ExplanationCache()
    return _instance
