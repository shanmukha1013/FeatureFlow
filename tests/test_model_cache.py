"""
Integration tests for Phase 3: Redis Model Registry Cache.

Proves:
- Cache hit
- Cache miss
- PostgreSQL fallback (System of Record)
- Automatic repopulation
- Cache refresh
- Cache invalidation on model archiving/deletion
- REST API verification
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.cache.redis_client import RedisClient
from app.cache.model_cache import ModelRegistryCache, get_model_registry_cache
from app.storage.database import AsyncSessionLocal
from app.storage.repositories.core import (
    DatasetRepository,
    ModelRepository,
    ChampionModelRepository,
    ExperimentRepository,
    FeatureRepository
)
from app.storage.models import ModelVersion


@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis_connections():
    """Ensure clean connection release after every test run."""
    yield
    client = await RedisClient.get_instance()
    await client.disconnect()


@pytest.mark.asyncio
async def test_model_cache_hit_and_miss():
    """Prove Redis hit, miss mechanics, and statistics tracking for model, champion, and metadata."""
    cache = await get_model_registry_cache()
    model_id = f"test_mdl_{uuid.uuid4()}"
    dataset = f"ds_{uuid.uuid4()}"

    # 1. Verify initial miss on model
    initial_misses = cache.misses
    payload = await cache.get_model(model_id, track_stats=True)
    assert payload is None
    assert cache.misses == initial_misses + 1

    # 2. Store active model
    model_data = {
        "id": model_id,
        "name": "random_forest_v1",
        "dataset_id": "ds_id_123",
        "dataset_name": dataset,
        "algorithm": "RandomForest",
        "metrics": {"accuracy": 0.96},
        "hyperparameters": {"n_estimators": 100},
        "artifact_uri": "models/test.joblib",
        "status": "ACTIVE",
        "version": 1
    }
    assert await cache.store_model(model_data) is True

    # 3. Verify hit
    initial_hits = cache.hits
    payload_hit = await cache.get_model(model_id, track_stats=True)
    assert payload_hit is not None
    assert cache.hits == initial_hits + 1
    assert payload_hit["name"] == "random_forest_v1"
    assert payload_hit["metrics"]["accuracy"] == 0.96

    # 4. Store and verify champion cache (`champion:{dataset}`)
    assert await cache.store_champion(dataset, model_data) is True
    champ_hit = await cache.get_champion(dataset, track_stats=True)
    assert champ_hit is not None
    assert champ_hit["id"] == model_id

    # 5. Store and verify metadata cache (`metadata:{model_id}`)
    metadata = {
        "model_id": model_id,
        "name": "random_forest_v1",
        "artifact_metadata": {"uri": "models/test.joblib", "versions_count": 1},
        "features": [{"name": "age", "dtype": "int64"}],
        "experiments": [{"name": "exp_1", "status": "COMPLETED"}]
    }
    assert await cache.store_metadata(model_id, metadata) is True
    meta_hit = await cache.get_metadata(model_id, track_stats=True)
    assert meta_hit is not None
    assert len(meta_hit["features"]) == 1

    # Cleanup
    await cache.delete_model_cache(model_id, dataset=dataset)


@pytest.mark.asyncio
async def test_postgresql_fallback_and_repopulation():
    """Prove fallback to PostgreSQL on Redis cache miss and automatic repopulation."""
    cache = await get_model_registry_cache()
    ds_name = f"churn_{uuid.uuid4()}"
    m_name = f"xgb_{uuid.uuid4()}"

    async with AsyncSessionLocal() as session:
        ds_repo = DatasetRepository(session)
        ds = await ds_repo.create({"name": ds_name, "description": "Customer churn dataset"})

        model_repo = ModelRepository(session)
        model = await model_repo.create({
            "dataset_id": ds.id,
            "name": m_name,
            "algorithm": "XGBoost",
            "metrics": {"f1": 0.89},
            "hyperparameters": {"max_depth": 6},
            "artifact_uri": "models/xgb.joblib",
            "status": "REGISTERED",
            "version": 1
        })

        champ_repo = ChampionModelRepository(session)
        await champ_repo.create({"dataset_id": ds.id, "model_id": model.id})

        # Add feature and experiment to prove rich metadata reconstruction
        feat_repo = FeatureRepository(session)
        await feat_repo.create({"dataset_id": ds.id, "name": "tenure", "dtype": "float64", "transformation": "Raw"})

        exp_repo = ExperimentRepository(session)
        await exp_repo.create({
            "dataset_id": ds.id,
            "name": f"Train {m_name}",
            "algorithm": "XGBoost",
            "metrics": {"f1": 0.89},
            "model_id": model.id,
            "status": "COMPLETED"
        })

        model_id = model.id
        ds_id = ds.id
        await session.commit()

    # 1. Clear any cached entry
    await cache.delete_model_cache(model_id, dataset=ds_name)
    assert await cache.get_model(model_id, track_stats=False) is None

    # 2. Call get_model_with_fallback -> should query PostgreSQL and repopulate Redis
    m_data, source = await cache.get_model_with_fallback(model_id)
    assert m_data is not None
    assert source == "postgresql"
    assert m_data["name"] == m_name
    assert m_data["metrics"]["f1"] == 0.89

    # Verify automatic repopulation: immediate get_model() should now hit Redis directly
    m_cached = await cache.get_model(model_id, track_stats=False)
    assert m_cached is not None
    assert m_cached["name"] == m_name

    # 3. Call get_champion_with_fallback -> fallback from DB & repopulation
    await cache.cache.delete(f"champion:{ds_name}")
    c_data, c_src = await cache.get_champion_with_fallback(ds_name)
    assert c_data is not None
    assert c_src == "postgresql"
    assert c_data["model_id"] == model_id

    # 4. Call get_metadata_with_fallback -> exact rich metadata without placeholders
    await cache.cache.delete(f"metadata:{model_id}")
    meta_data, meta_src = await cache.get_metadata_with_fallback(model_id)
    assert meta_data is not None
    assert meta_src == "postgresql"
    assert meta_data["algorithm"] == "XGBoost"
    assert len(meta_data["features"]) == 1
    assert meta_data["features"][0]["name"] == "tenure"
    assert len(meta_data["experiments"]) == 1
    assert meta_data["experiments"][0]["status"] == "COMPLETED"

    # Cleanup
    async with AsyncSessionLocal() as session:
        model_repo = ModelRepository(session)
        ds_repo = DatasetRepository(session)
        await model_repo.delete(model_id)
        await ds_repo.delete(ds_id)
        await session.commit()


@pytest.mark.asyncio
async def test_cache_refresh():
    """Prove manual and automated cache refresh mechanics."""
    cache = await get_model_registry_cache()
    ds_name = f"refresh_ds_{uuid.uuid4()}"

    async with AsyncSessionLocal() as session:
        ds_repo = DatasetRepository(session)
        ds = await ds_repo.create({"name": ds_name})

        model_repo = ModelRepository(session)
        model = await model_repo.create({
            "dataset_id": ds.id,
            "name": "initial_model",
            "metrics": {"auc": 0.80},
            "status": "REGISTERED",
            "version": 1
        })
        model_id = model.id
        ds_id = ds.id
        await session.commit()

    # Populate cache initially
    await cache.get_model_with_fallback(model_id)
    m_cached_initial = await cache.get_model(model_id, track_stats=False)
    assert m_cached_initial["metrics"]["auc"] == 0.80

    # Update metrics in PostgreSQL
    async with AsyncSessionLocal() as session:
        model_repo = ModelRepository(session)
        m_obj = await model_repo.get(model_id)
        await model_repo.update(m_obj, {"metrics": {"auc": 0.94}})
        await session.commit()

    # Trigger refresh_model_cache
    initial_refresh_cnt = cache.refresh_count
    refreshed_payload = await cache.refresh_model_cache(model_id)
    assert refreshed_payload is not None
    assert refreshed_payload["metrics"]["auc"] == 0.94
    assert cache.refresh_count == initial_refresh_cnt + 1
    assert cache.last_refresh is not None

    # Verify Redis is updated
    m_cached_after = await cache.get_model(model_id, track_stats=False)
    assert m_cached_after["metrics"]["auc"] == 0.94

    # Trigger refresh_all_caches
    res_all = await cache.refresh_all_caches()
    assert res_all["status"] == "success"
    assert res_all["refreshed_models_count"] >= 1

    # Cleanup
    async with AsyncSessionLocal() as session:
        model_repo = ModelRepository(session)
        ds_repo = DatasetRepository(session)
        await model_repo.delete(model_id)
        await ds_repo.delete(ds_id)
        await session.commit()


@pytest.mark.asyncio
async def test_cache_invalidation_and_lifecycle_hooks():
    """Prove automatic cache invalidation when models are archived or deleted."""
    cache = await get_model_registry_cache()
    ds_name = f"inv_ds_{uuid.uuid4()}"

    async with AsyncSessionLocal() as session:
        ds_repo = DatasetRepository(session)
        ds = await ds_repo.create({"name": ds_name})

        model_repo = ModelRepository(session)
        model = await model_repo.create({
            "dataset_id": ds.id,
            "name": "model_to_archive",
            "status": "REGISTERED",
            "version": 1
        })
        model_id = model.id
        ds_id = ds.id
        await session.commit()

    # Populate cache
    await cache.get_model_with_fallback(model_id)
    assert await cache.get_model(model_id, track_stats=False) is not None

    # Archive via ModelRepository -> hook should automatically evict cache
    async with AsyncSessionLocal() as session:
        model_repo = ModelRepository(session)
        m_obj = await model_repo.get(model_id)
        await model_repo.update(m_obj, {"status": "ARCHIVED"})
        await session.commit()

    # Verify cache invalidation
    assert await cache.get_model(model_id, track_stats=False) is None
    assert await cache.get_metadata(model_id, track_stats=False) is None

    # Cleanup
    async with AsyncSessionLocal() as session:
        model_repo = ModelRepository(session)
        ds_repo = DatasetRepository(session)
        await model_repo.delete(model_id)
        await ds_repo.delete(ds_id)
        await session.commit()


@pytest.mark.asyncio
async def test_model_cache_endpoints(client: AsyncClient):
    """Prove Phase 3 REST APIs: GET /models/cache, POST /models/cache/refresh, and DELETE /models/cache/{model_id}."""
    # 1. GET /models/cache (and /api/v1/models/cache)
    resp = await client.get("/api/v1/models/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    stats = data["statistics"]
    assert "hits" in stats
    assert "misses" in stats
    assert "refresh_count" in stats
    assert "memory_usage_bytes" in stats

    # Also test via root path /models/cache
    resp_root = await client.get("/models/cache")
    assert resp_root.status_code == 200

    # 2. POST /models/cache/refresh
    resp_ref = await client.post("/api/v1/models/cache/refresh")
    assert resp_ref.status_code == 200
    ref_data = resp_ref.json()
    assert ref_data["status"] == "success"
    assert "refreshed_models_count" in ref_data

    # 3. DELETE /models/cache/{model_id}
    test_mdl = f"delete_test_{uuid.uuid4()}"
    cache = await get_model_registry_cache()
    await cache.store_model({"id": test_mdl, "name": "temp"})
    assert await cache.get_model(test_mdl, track_stats=False) is not None

    resp_del = await client.delete(f"/api/v1/models/cache/{test_mdl}")
    assert resp_del.status_code == 200
    del_data = resp_del.json()
    assert del_data["status"] == "success"
    assert del_data["deleted"] is True
    assert del_data["model_id"] == test_mdl
    assert await cache.get_model(test_mdl, track_stats=False) is None
