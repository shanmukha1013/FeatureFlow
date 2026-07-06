import time
import json
from typing import Dict, Any, Optional
from app.utils.logger import get_logger
from app.monitoring.audit import AuditLogger, AuditEvent

logger = get_logger(__name__)

class RedisOnlineStore:
    """
    Online Feature Store for Low-Latency Inference.
    Note: Uses in-memory dictionary to guarantee execution without a standalone Redis daemon.
    In enterprise, this uses `redis-py` pointing to ElastiCache.
    """
    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        
        self.stats = {
            "hits": 0,
            "misses": 0,
            "size_bytes": 0
        }

    def _get_key(self, entity_id: str) -> str:
        return f"entity_features:{entity_id}"

    def write(self, entity_id: str, features: Dict[str, Any]):
        key = self._get_key(entity_id)
        # Store with expiry
        self._cache[key] = {
            "data": features,
            "expires_at": time.time() + self._ttl
        }
        self._update_size()

    def read(self, entity_id: str) -> Optional[Dict[str, Any]]:
        key = self._get_key(entity_id)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry["expires_at"]:
                self.stats["hits"] += 1
                AuditLogger.record(AuditEvent(event_name="REDIS_CACHE_HIT", component="RedisOnlineStore", severity="INFO", payload={"entity_id": entity_id}))
                return entry["data"]
            else:
                # Expired
                del self._cache[key]
                
        self.stats["misses"] += 1
        AuditLogger.record(AuditEvent(event_name="REDIS_CACHE_MISS", component="RedisOnlineStore", severity="INFO", payload={"entity_id": entity_id}))
        return None

    def _update_size(self):
        # Rough estimation of memory usage
        self.stats["size_bytes"] = len(json.dumps(self._cache).encode('utf-8'))

global_online_store = RedisOnlineStore()
