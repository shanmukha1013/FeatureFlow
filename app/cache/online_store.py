"""
Online Feature Store abstraction for FeatureFlow using Redis Cloud.

Implements Phase 2 requirements:
- Storing engineered feature vectors with entity-based keys (feature:{dataset}:{entity_id})
- Persisting values, names, feature version, timestamp, and dataset version
- High-performance single and batch feature lookups
- Automatic fallback to PostgreSQL (Offline Feature Store / System of Record) on cache miss
- Configurable TTL expiration (`settings.redis_feature_ttl`)
- Version invalidation on dataset/model retraining
- Comprehensive hit/miss telemetry statistics
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union, Tuple

from app.cache.cache_manager import CacheManager, get_cache_manager
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OnlineFeatureStore:
    """
    Production-grade Online Feature Store backed by Redis Cloud.

    Acts as a high-speed serving layer while preserving PostgreSQL as the single
    authoritative source of truth (`Offline Feature Store`).
    """
    _instance: Optional["OnlineFeatureStore"] = None
    _lock = asyncio.Lock()

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager or get_cache_manager()
        self.hits: int = 0
        self.misses: int = 0

    @classmethod
    async def get_instance(cls) -> "OnlineFeatureStore":
        """Returns singleton instance of the OnlineFeatureStore."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "OnlineFeatureStore":
        """Synchronous singleton accessor for dependency injection."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _make_key(self, dataset: str, entity_id: str) -> str:
        """Constructs standardized entity-based Redis key."""
        return f"feature:{dataset}:{entity_id}"

    async def store_online_features(
        self,
        dataset: str,
        entity_id: str,
        feature_values: Dict[str, Any],
        feature_version: Union[int, str] = 1,
        dataset_version: Union[str, int] = 1,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Writes an entity's engineered feature vector and metadata into Redis.
        """
        key = self._make_key(dataset, entity_id)
        effective_ttl = ttl if ttl is not None else settings.redis_feature_ttl

        payload = {
            "values": feature_values,
            "names": list(feature_values.keys()),
            "version": feature_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_version": dataset_version
        }
        return await self.cache.set_json(key, payload, ttl=effective_ttl)

    async def get_online_features(
        self,
        dataset: str,
        entity_id: str,
        track_stats: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Queries Redis for an entity feature vector.
        Tracks hit/miss statistics.
        """
        key = self._make_key(dataset, entity_id)
        payload = await self.cache.get_json(key)

        if track_stats:
            if payload is not None:
                self.hits += 1
            else:
                self.misses += 1

        return payload

    async def get_online_features_batch(
        self,
        dataset: str,
        entity_ids: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Batch queries Redis for multiple entities in a single roundtrip.
        """
        if not entity_ids:
            return {}

        keys = [self._make_key(dataset, eid) for eid in entity_ids]
        raw_map = await self.cache.get_multi(keys)

        result: Dict[str, Optional[Dict[str, Any]]] = {}
        import json
        for eid, key in zip(entity_ids, keys):
            raw = raw_map.get(key)
            if raw:
                try:
                    payload = json.loads(raw)
                    self.hits += 1
                    result[eid] = payload
                except Exception as e:
                    logger.warning(f"Failed to decode batch feature JSON for key {key}: {e}")
                    self.misses += 1
                    result[eid] = None
            else:
                self.misses += 1
                result[eid] = None

        return result

    async def store_online_features_batch(
        self,
        dataset: str,
        entity_features_map: Dict[str, Dict[str, Any]],
        feature_version: Union[int, str] = 1,
        dataset_version: Union[str, int] = 1,
        ttl: Optional[int] = None
    ) -> Dict[str, bool]:
        """
        Batch writes multiple entity feature vectors to Redis concurrently.
        """
        effective_ttl = ttl if ttl is not None else settings.redis_feature_ttl
        tasks = [
            self.store_online_features(
                dataset=dataset,
                entity_id=eid,
                feature_values=fvals,
                feature_version=feature_version,
                dataset_version=dataset_version,
                ttl=effective_ttl
            )
            for eid, fvals in entity_features_map.items()
        ]
        if not tasks:
            return {}

        results = await asyncio.gather(*tasks)
        return {eid: res for eid, res in zip(entity_features_map.keys(), results)}

    async def delete_online_features(self, dataset: str, entity_id: str) -> bool:
        """Deletes an entity's feature vector from Redis."""
        key = self._make_key(dataset, entity_id)
        return await self.cache.delete(key)

    async def refresh_online_features(
        self,
        dataset: str,
        entity_id: str,
        ttl: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Queries PostgreSQL (System of Record) for an entity's feature values,
        reconstructs the feature vector, stores it into Redis, and returns the payload.
        """
        try:
            from app.storage.database import AsyncSessionLocal
            from app.storage.repositories.core import FeatureValueRepository, DatasetRepository

            async with AsyncSessionLocal() as session:
                # Resolve dataset ID if dataset parameter is a name
                ds_repo = DatasetRepository(session)
                ds_obj = await ds_repo.get_by_name(dataset)
                if not ds_obj:
                    # Maybe dataset parameter passed is already the UUID
                    ds_obj = await ds_repo.get_by_id(dataset)

                ds_id = ds_obj.id if ds_obj else dataset
                ds_version = ds_obj.version if ds_obj else 1

                fv_repo = FeatureValueRepository(session)
                fvs = await fv_repo.get_by_entity(entity_id=entity_id, dataset_id=ds_id)

                if not fvs:
                    logger.debug(f"No offline features in PostgreSQL for entity '{entity_id}' in dataset '{dataset}'.")
                    return None

                # Reconstruct feature values dictionary from authoritative PostgreSQL records
                feature_values: Dict[str, Any] = {}
                max_version = 1
                for fv in fvs:
                    if fv.feature and fv.feature.name:
                        # Extract primitive from JSONB or dict
                        val = fv.value_json
                        if isinstance(val, dict) and "value" in val:
                            feature_values[fv.feature.name] = val["value"]
                        else:
                            feature_values[fv.feature.name] = val
                    if fv.version and fv.version > max_version:
                        max_version = fv.version

                if not feature_values:
                    return None

                # Store reconstructed vector into Redis (repopulation)
                await self.store_online_features(
                    dataset=dataset,
                    entity_id=entity_id,
                    feature_values=feature_values,
                    feature_version=max_version,
                    dataset_version=ds_version,
                    ttl=ttl
                )

                return {
                    "values": feature_values,
                    "names": list(feature_values.keys()),
                    "version": max_version,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dataset_version": ds_version
                }
        except Exception as e:
            logger.error(f"Error refreshing online features from PostgreSQL for {dataset}:{entity_id}: {e}")
            return None

    async def get_online_features_with_fallback(
        self,
        dataset: str,
        entity_id: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Executes prediction/lookup flow:
        1. Query Redis (if hit, return immediately).
        2. If miss, load from PostgreSQL, reconstruct, store in Redis, and return.

        Returns tuple of (feature_payload, source) where source is 'redis' or 'postgresql'.
        """
        # 1. Query Redis first
        payload = await self.get_online_features(dataset, entity_id, track_stats=True)
        if payload is not None:
            return payload, "redis"

        # 2. On Miss, fall back to PostgreSQL offline store & repopulate Redis
        logger.info(f"Online store cache miss for {dataset}:{entity_id}. Loading from PostgreSQL offline store.")
        payload = await self.refresh_online_features(dataset, entity_id)
        if payload is not None:
            return payload, "postgresql"

        return None, "miss"

    async def invalidate_dataset_features(
        self,
        dataset: str,
        version: Optional[Union[str, int]] = None
    ) -> int:
        """
        Automatically invalidates outdated feature versions in Redis after retraining
        or feature pipeline updates.
        """
        async def _scan_and_delete(client) -> int:
            match_pattern = self._make_key(dataset, "*")
            keys_to_delete = []
            async for key in client.scan_iter(match=match_pattern):
                keys_to_delete.append(key)

            if not keys_to_delete:
                return 0

            if version is not None:
                # If a specific old version is targeted, check payload versions before deleting
                raw_map = await client.mget(keys_to_delete)
                filtered_keys = []
                import json
                for key, raw in zip(keys_to_delete, raw_map):
                    if raw:
                        try:
                            meta = json.loads(raw)
                            if str(meta.get("version", "")) == str(version) or str(meta.get("dataset_version", "")) == str(version):
                                filtered_keys.append(key)
                        except Exception:
                            filtered_keys.append(key)
                keys_to_delete = filtered_keys

            if keys_to_delete:
                return await client.delete(*keys_to_delete)
            return 0

        res = await self.cache.redis.execute_with_retry(_scan_and_delete)
        try:
            from app.cache.prediction_cache import get_prediction_cache
            pcache = await get_prediction_cache()
            await pcache.invalidate_cache(dataset=dataset)
        except Exception as e:
            logger.debug(f"Could not invalidate prediction cache from online store: {e}")
        return int(res or 0)

    def get_stats(self) -> Dict[str, Any]:
        """Returns real-time telemetry on Redis hit/miss statistics."""
        total = self.hits + self.misses
        hit_rate = round((self.hits / total) * 100.0, 2) if total > 0 else 0.0
        return {
            "redis_hits": self.hits,
            "redis_misses": self.misses,
            "total_lookups": total,
            "hit_rate_percent": hit_rate
        }


def get_online_store() -> OnlineFeatureStore:
    """Synchronous accessor for dependency injection."""
    return OnlineFeatureStore.get_instance_sync()
