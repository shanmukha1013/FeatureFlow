"""
Redis Model Registry Cache (Phase 3).

Acts as a high-speed online cache for model metadata, champion models, active models,
artifact metadata, feature lists, and experiment summaries while maintaining PostgreSQL
as the authoritative System of Record.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from app.cache.redis_client import RedisClient
from app.cache.cache_manager import CacheManager
from app.config import settings

logger = logging.getLogger(__name__)


class ModelRegistryCache:
    """
    Manages Redis caching for the Model Registry.

    Cache Keys:
      - model:{model_id}
      - champion:{dataset}
      - metadata:{model_id}
    """
    _instance: Optional['ModelRegistryCache'] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, redis_client: Optional[RedisClient] = None, cache_manager: Optional[CacheManager] = None):
        self.redis = redis_client or RedisClient.get_instance_sync()
        from app.cache.cache_manager import CacheManager
        self.cache = cache_manager or CacheManager(self.redis)

        # Statistics tracking
        self.hits: int = 0
        self.misses: int = 0
        self.refresh_count: int = 0
        self.last_refresh: Optional[str] = None

    @classmethod
    async def get_instance(cls) -> 'ModelRegistryCache':
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if cls._instance is not None and hasattr(cls._instance, '_loop') and cls._instance._loop != current_loop:
            cls._instance = None

        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    redis_client = await RedisClient.get_instance()
                    from app.cache.cache_manager import CacheManager
                    cache_manager = CacheManager(redis_client)
                    cls._instance = cls(redis_client, cache_manager)
                    if current_loop:
                        cls._instance._loop = current_loop
        return cls._instance

    async def get_stats(self) -> Dict[str, Any]:
        """Returns real-time cache statistics including memory usage from Redis."""
        memory_bytes = 0
        try:
            async def _info_op(client):
                return await client.info(section="memory")
            info = await self.redis.execute_with_retry(_info_op)
            if info and isinstance(info, dict):
                memory_bytes = int(info.get("used_memory", 0))
        except Exception as e:
            logger.debug(f"Failed to fetch Redis memory stats: {e}")

        return {
            "hits": self.hits,
            "misses": self.misses,
            "refresh_count": self.refresh_count,
            "last_refresh": self.last_refresh,
            "memory_usage_bytes": memory_bytes
        }

    # --- Cache Lookup & Storage Methods ---

    async def get_model(self, model_id: str, track_stats: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieves active model payload from Redis cache (`model:{model_id}`)."""
        key = f"model:{model_id}"
        payload = await self.cache.get_json(key)
        if track_stats:
            if payload is not None:
                self.hits += 1
            else:
                self.misses += 1
        return payload

    async def store_model(self, model_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Stores model payload into Redis cache (`model:{model_id}`)."""
        model_id = model_data.get("id")
        if not model_id:
            return False
        key = f"model:{model_id}"
        effective_ttl = ttl if ttl is not None else getattr(settings, "redis_model_ttl", 3600)
        return await self.cache.set_json(key, model_data, ttl=effective_ttl)

    async def get_champion(self, dataset: str, track_stats: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieves champion model payload from Redis cache (`champion:{dataset}`)."""
        key = f"champion:{dataset}"
        payload = await self.cache.get_json(key)
        if track_stats:
            if payload is not None:
                self.hits += 1
            else:
                self.misses += 1
        return payload

    async def store_champion(self, dataset: str, champion_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Stores champion model payload into Redis cache (`champion:{dataset}`)."""
        if not dataset:
            return False
        key = f"champion:{dataset}"
        effective_ttl = ttl if ttl is not None else getattr(settings, "redis_model_ttl", 3600)
        success = await self.cache.set_json(key, champion_data, ttl=effective_ttl)

        # Also store by dataset_id if present so lookup by UUID or name both succeed
        dataset_id = champion_data.get("dataset_id")
        if dataset_id and dataset_id != dataset:
            await self.cache.set_json(f"champion:{dataset_id}", champion_data, ttl=effective_ttl)
        return success

    async def get_metadata(self, model_id: str, track_stats: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieves comprehensive model metadata (`metadata:{model_id}`)."""
        key = f"metadata:{model_id}"
        payload = await self.cache.get_json(key)
        if track_stats:
            if payload is not None:
                self.hits += 1
            else:
                self.misses += 1
        return payload

    async def store_metadata(self, model_id: str, metadata: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Stores comprehensive model metadata (`metadata:{model_id}`)."""
        if not model_id:
            return False
        key = f"metadata:{model_id}"
        effective_ttl = ttl if ttl is not None else getattr(settings, "redis_model_ttl", 3600)
        return await self.cache.set_json(key, metadata, ttl=effective_ttl)

    async def delete_model_cache(self, model_id: str, dataset: Optional[str] = None) -> bool:
        """
        Evicts model metadata from Redis cache (`model:{model_id}`, `metadata:{model_id}`,
        and optionally `champion:{dataset}` if this model was champion).
        """
        keys_to_del = [f"model:{model_id}", f"metadata:{model_id}"]
        if dataset:
            keys_to_del.append(f"champion:{dataset}")

        # Also check if this model_id is currently champion for any dataset
        try:
            async def _keys_op(client):
                return await client.keys("champion:*")
            champ_keys = await self.redis.execute_with_retry(_keys_op)
            if champ_keys:
                for ckey in champ_keys:
                    key_str = ckey.decode() if isinstance(ckey, bytes) else ckey
                    cdata = await self.cache.get_json(key_str)
                    if cdata and cdata.get("model_id") == model_id:
                        keys_to_del.append(key_str)
        except Exception as e:
            logger.debug(f"Error checking champion keys during eviction for {model_id}: {e}")

        for k in set(keys_to_del):
            await self.cache.delete(k)
        return True

    # --- Fallback & Repopulation Methods (Requirement 3 & 4) ---

    async def get_model_with_fallback(self, model_id: str, session: Optional[Any] = None) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Checks Redis first (`model:{model_id}`).
        If missing (`miss`), falls back to PostgreSQL, constructs model dict,
        and repopulates Redis.
        """
        cached = await self.get_model(model_id, track_stats=True)
        if cached is not None:
            return cached, "redis"

        # Fallback to PostgreSQL
        try:
            from app.storage.database import AsyncSessionLocal
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select
            from app.storage.models import Model

            async def _fetch(sess):
                result = await sess.execute(
                    select(Model).options(selectinload(Model.dataset)).filter(Model.id == model_id, Model.status != "ARCHIVED")
                )
                model_obj = result.scalars().first()
                if not model_obj:
                    return None
                ds_name = model_obj.dataset.name if model_obj.dataset else ""
                return {
                    "id": model_obj.id,
                    "name": model_obj.name,
                    "dataset_id": model_obj.dataset_id,
                    "dataset_name": ds_name,
                    "algorithm": model_obj.algorithm,
                    "metrics": model_obj.metrics or {},
                    "hyperparameters": model_obj.hyperparameters or {},
                    "artifact_uri": model_obj.artifact_uri,
                    "status": model_obj.status,
                    "version": model_obj.version,
                    "created_at": model_obj.created_at.isoformat() if model_obj.created_at else None,
                    "updated_at": model_obj.updated_at.isoformat() if model_obj.updated_at else None
                }

            if session:
                model_data = await _fetch(session)
            else:
                async with AsyncSessionLocal() as s:
                    model_data = await _fetch(s)

            if not model_data:
                return None, "missing"

            # Automatically repopulate Redis
            await self.store_model(model_data)
            return model_data, "postgresql"
        except Exception as e:
            logger.error(f"PostgreSQL fallback failed for model {model_id}: {e}")
            return None, "error"

    async def get_champion_with_fallback(self, dataset: str, session: Optional[Any] = None) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Checks Redis first (`champion:{dataset}`).
        If missing (`miss`), queries PostgreSQL (`ChampionModel` + `Model`), constructs champion data,
        and repopulates Redis (`champion:{dataset}` and `champion:{dataset_id}`).
        """
        cached = await self.get_champion(dataset, track_stats=True)
        if cached is not None:
            return cached, "redis"

        # Fallback to PostgreSQL
        try:
            from app.storage.database import AsyncSessionLocal
            from app.storage.repositories.core import DatasetRepository
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select
            from app.storage.models import ChampionModel

            async def _fetch(sess):
                ds_repo = DatasetRepository(sess)
                ds_obj = await ds_repo.get_by_name(dataset)
                if not ds_obj:
                    ds_obj = await ds_repo.get(dataset)

                if not ds_obj:
                    return None, None

                result = await sess.execute(
                    select(ChampionModel)
                    .options(selectinload(ChampionModel.model))
                    .filter(ChampionModel.dataset_id == ds_obj.id, ChampionModel.status != "ARCHIVED")
                )
                champ_obj = result.scalars().first()
                if not champ_obj or not champ_obj.model:
                    return None, None

                model_obj = champ_obj.model
                return ds_obj, {
                    "dataset": ds_obj.name,
                    "dataset_id": ds_obj.id,
                    "model_id": model_obj.id,
                    "name": model_obj.name,
                    "algorithm": model_obj.algorithm,
                    "metrics": model_obj.metrics or {},
                    "hyperparameters": model_obj.hyperparameters or {},
                    "artifact_uri": model_obj.artifact_uri,
                    "status": "ACTIVE",
                    "version": model_obj.version,
                    "created_at": model_obj.created_at.isoformat() if model_obj.created_at else None
                }

            if session:
                ds_obj, champion_data = await _fetch(session) or (None, None)
            else:
                async with AsyncSessionLocal() as s:
                    ds_obj, champion_data = await _fetch(s) or (None, None)

            if not ds_obj or not champion_data:
                return None, "missing"

            # Automatically repopulate Redis
            await self.store_champion(ds_obj.name, champion_data)
            await self.store_champion(ds_obj.id, champion_data)
            return champion_data, "postgresql"
        except Exception as e:
            logger.error(f"PostgreSQL fallback failed for champion on dataset '{dataset}': {e}")
            return None, "error"

    async def get_metadata_with_fallback(self, model_id: str, session: Optional[Any] = None) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Checks Redis first (`metadata:{model_id}`).
        If missing, queries PostgreSQL (`Model`, `ModelVersion`, `ModelArtifact`, `Feature`, `Experiment`),
        reconstructs comprehensive metadata without placeholders or mock data, and repopulates Redis.
        """
        cached = await self.get_metadata(model_id, track_stats=True)
        if cached is not None:
            return cached, "redis"

        try:
            from app.storage.database import AsyncSessionLocal
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.storage.models import Model, ModelVersion, Feature, Experiment

            async def _fetch(sess):
                # 1. Fetch Model
                m_res = await sess.execute(
                    select(Model).options(selectinload(Model.dataset)).filter(Model.id == model_id, Model.status != "ARCHIVED")
                )
                model_obj = m_res.scalars().first()
                if not model_obj:
                    return None

                # 2. Fetch versions and artifacts
                v_res = await sess.execute(
                    select(ModelVersion).options(selectinload(ModelVersion.artifacts)).filter(ModelVersion.model_id == model_id)
                )
                versions = v_res.scalars().all()
                versions_count = len(versions)
                latest_tag = f"v{model_obj.version}"
                if versions:
                    latest_ver = max(versions, key=lambda v: v.version)
                    latest_tag = latest_ver.version_tag

                artifact_meta = {
                    "uri": model_obj.artifact_uri,
                    "versions_count": versions_count,
                    "latest_version_tag": latest_tag
                }

                # 3. Fetch feature lists for this dataset
                features_list = []
                if model_obj.dataset_id:
                    f_res = await sess.execute(
                        select(Feature).filter(Feature.dataset_id == model_obj.dataset_id, Feature.status != "ARCHIVED")
                    )
                    features = f_res.scalars().all()
                    for feat in features:
                        features_list.append({
                            "id": feat.id,
                            "name": feat.name,
                            "dtype": feat.dtype,
                            "transformation": feat.transformation
                        })

                # 4. Fetch experiment summaries associated with this model or dataset
                experiments_list = []
                if model_obj.dataset_id:
                    exp_res = await sess.execute(
                        select(Experiment).filter(
                            (Experiment.model_id == model_id) | (Experiment.dataset_id == model_obj.dataset_id),
                            Experiment.status != "ARCHIVED"
                        )
                    )
                    exps = exp_res.scalars().all()
                    for exp in exps:
                        experiments_list.append({
                            "id": exp.id,
                            "name": exp.name,
                            "algorithm": exp.algorithm,
                            "metrics": exp.metrics or {},
                            "status": exp.status,
                            "end_time": exp.end_time.isoformat() if exp.end_time else None
                        })

                return {
                    "model_id": model_obj.id,
                    "name": model_obj.name,
                    "algorithm": model_obj.algorithm,
                    "metrics": model_obj.metrics or {},
                    "hyperparameters": model_obj.hyperparameters or {},
                    "artifact_metadata": artifact_meta,
                    "features": features_list,
                    "experiments": experiments_list,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            if session:
                metadata = await _fetch(session)
            else:
                async with AsyncSessionLocal() as s:
                    metadata = await _fetch(s)

            if not metadata:
                return None, "missing"

            # Repopulate Redis
            await self.store_metadata(model_id, metadata)
            return metadata, "postgresql"
        except Exception as e:
            logger.error(f"PostgreSQL fallback failed for metadata {model_id}: {e}")
            return None, "error"

    # --- Cache Refresh Methods (Requirement 4) ---

    async def refresh_model_cache(self, model_id: str, session: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Refreshes `model:{model_id}` and `metadata:{model_id}` from authoritative PostgreSQL records."""
        # Force a miss and fallback lookup to rebuild cached payloads
        await self.delete_model_cache(model_id)
        model_data, _ = await self.get_model_with_fallback(model_id, session=session)
        if model_data:
            await self.get_metadata_with_fallback(model_id, session=session)
            self.refresh_count += 1
            self.last_refresh = datetime.now(timezone.utc).isoformat()
        return model_data

    async def refresh_champion_cache(self, dataset: str, session: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Refreshes `champion:{dataset}` from authoritative PostgreSQL records."""
        await self.cache.delete(f"champion:{dataset}")
        champ_data, _ = await self.get_champion_with_fallback(dataset, session=session)
        if champ_data:
            self.refresh_count += 1
            self.last_refresh = datetime.now(timezone.utc).isoformat()
        return champ_data

    async def refresh_all_caches(self) -> Dict[str, Any]:
        """Queries all active models and champions from PostgreSQL and refreshes all cache entries concurrently."""
        try:
            from app.storage.database import AsyncSessionLocal
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.storage.models import Model, ChampionModel, ModelVersion, Feature, Experiment

            refreshed_models = 0
            refreshed_champions = 0

            async with AsyncSessionLocal() as session:
                # 1. Fetch all active models
                m_res = await session.execute(
                    select(Model).options(selectinload(Model.dataset)).filter(Model.status != "ARCHIVED")
                )
                models = m_res.scalars().all()
                model_ids = [m.id for m in models]
                dataset_ids = [m.dataset_id for m in models if m.dataset_id]

                # 2. Fetch all champions
                c_res = await session.execute(
                    select(ChampionModel).options(selectinload(ChampionModel.model).selectinload(Model.dataset)).filter(ChampionModel.status != "ARCHIVED")
                )
                champions = c_res.scalars().all()

                # 3. Bulk fetch versions, features, experiments for all active models
                versions_by_model = {}
                if model_ids:
                    v_res = await session.execute(
                        select(ModelVersion).options(selectinload(ModelVersion.artifacts)).filter(ModelVersion.model_id.in_(model_ids))
                    )
                    for v in v_res.scalars().all():
                        versions_by_model.setdefault(v.model_id, []).append(v)

                features_by_dataset = {}
                if dataset_ids:
                    f_res = await session.execute(
                        select(Feature).filter(Feature.dataset_id.in_(dataset_ids), Feature.status != "ARCHIVED")
                    )
                    for f in f_res.scalars().all():
                        features_by_dataset.setdefault(f.dataset_id, []).append(f)

                experiments_by_model_or_ds = {}
                if model_ids or dataset_ids:
                    exp_res = await session.execute(
                        select(Experiment).filter(
                            (Experiment.model_id.in_(model_ids)) | (Experiment.dataset_id.in_(dataset_ids)),
                            Experiment.status != "ARCHIVED"
                        )
                    )
                    for exp in exp_res.scalars().all():
                        if exp.model_id:
                            experiments_by_model_or_ds.setdefault(f"m_{exp.model_id}", []).append(exp)
                        if exp.dataset_id:
                            experiments_by_model_or_ds.setdefault(f"ds_{exp.dataset_id}", []).append(exp)

                redis_tasks = []
                for m in models:
                    ds_name = m.dataset.name if m.dataset else ""
                    model_data = {
                        "id": m.id,
                        "name": m.name,
                        "dataset_id": m.dataset_id,
                        "dataset_name": ds_name,
                        "algorithm": m.algorithm,
                        "metrics": m.metrics or {},
                        "hyperparameters": m.hyperparameters or {},
                        "artifact_uri": m.artifact_uri,
                        "status": m.status,
                        "version": m.version,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                        "updated_at": m.updated_at.isoformat() if m.updated_at else None
                    }
                    redis_tasks.append(self.store_model(model_data))

                    # Reconstruct exact metadata for this model
                    versions = versions_by_model.get(m.id, [])
                    versions_count = len(versions)
                    latest_tag = f"v{m.version}"
                    if versions:
                        latest_ver = max(versions, key=lambda v: v.version)
                        latest_tag = latest_ver.version_tag

                    artifact_meta = {
                        "uri": m.artifact_uri,
                        "versions_count": versions_count,
                        "latest_version_tag": latest_tag
                    }

                    features_list = [
                        {
                            "id": feat.id,
                            "name": feat.name,
                            "dtype": feat.dtype,
                            "transformation": feat.transformation
                        }
                        for feat in features_by_dataset.get(m.dataset_id, [])
                    ] if m.dataset_id else []

                    exps = []
                    exps.extend(experiments_by_model_or_ds.get(f"m_{m.id}", []))
                    if m.dataset_id:
                        for e_ds in experiments_by_model_or_ds.get(f"ds_{m.dataset_id}", []):
                            if e_ds not in exps:
                                exps.append(e_ds)

                    experiments_list = [
                        {
                            "id": exp.id,
                            "name": exp.name,
                            "algorithm": exp.algorithm,
                            "metrics": exp.metrics or {},
                            "status": exp.status,
                            "end_time": exp.end_time.isoformat() if exp.end_time else None
                        }
                        for exp in exps
                    ]

                    metadata = {
                        "model_id": m.id,
                        "name": m.name,
                        "algorithm": m.algorithm,
                        "metrics": m.metrics or {},
                        "hyperparameters": m.hyperparameters or {},
                        "artifact_metadata": artifact_meta,
                        "features": features_list,
                        "experiments": experiments_list,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    redis_tasks.append(self.store_metadata(m.id, metadata))
                    refreshed_models += 1

                for c in champions:
                    if c.model and c.model.dataset:
                        ds = c.model.dataset
                        model_obj = c.model
                        champion_data = {
                            "dataset": ds.name,
                            "dataset_id": ds.id,
                            "model_id": model_obj.id,
                            "name": model_obj.name,
                            "algorithm": model_obj.algorithm,
                            "metrics": model_obj.metrics or {},
                            "hyperparameters": model_obj.hyperparameters or {},
                            "artifact_uri": model_obj.artifact_uri,
                            "status": "ACTIVE",
                            "version": model_obj.version,
                            "created_at": model_obj.created_at.isoformat() if model_obj.created_at else None
                        }
                        redis_tasks.append(self.store_champion(ds.name, champion_data))
                        redis_tasks.append(self.store_champion(ds.id, champion_data))
                        refreshed_champions += 1

            if redis_tasks:
                for i in range(0, len(redis_tasks), 8):
                    await asyncio.gather(*redis_tasks[i:i + 8])

            self.refresh_count += 1
            self.last_refresh = datetime.now(timezone.utc).isoformat()
            return {
                "status": "success",
                "refreshed_models_count": refreshed_models,
                "refreshed_champions_count": refreshed_champions,
                "statistics": await self.get_stats()
            }
        except Exception as e:
            logger.error(f"Failed to refresh all model caches: {e}")
            return {
                "status": "error",
                "error": str(e),
                "statistics": await self.get_stats()
            }


async def get_model_registry_cache() -> ModelRegistryCache:
    """Convenience helper to fetch the singleton instance."""
    return await ModelRegistryCache.get_instance()
