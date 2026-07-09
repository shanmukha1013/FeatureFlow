"""
Integration tests for Phase 2: Redis Online Feature Store.

Proves:
- Redis hit
- Redis miss
- PostgreSQL fallback (Offline Store)
- Redis repopulation
- Configurable TTL expiration
- Batch operations (store & lookup)
- Version invalidation on dataset/model updates
- REST API endpoint verification
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.cache.redis_client import RedisClient
from app.cache.online_store import OnlineFeatureStore, get_online_store
from app.storage.database import AsyncSessionLocal
from app.storage.repositories.core import DatasetRepository, FeatureRepository, FeatureValueRepository


@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis_connections():
    """Ensure clean connection release after every test run."""
    yield
    client = await RedisClient.get_instance()
    await client.disconnect()


@pytest.mark.asyncio
async def test_online_store_hit_and_miss():
    """Prove Redis hit and Redis miss mechanics and statistics tracking."""
    store = OnlineFeatureStore()
    dataset = "ff_test:churn"
    entity_id = "user_101"

    # Verify initial miss
    payload = await store.get_online_features(dataset, entity_id, track_stats=True)
    assert payload is None
    assert store.misses == 1

    # Store feature vector
    fvals = {"age": 34, "balance": 1250.50}
    assert await store.store_online_features(dataset, entity_id, fvals, feature_version=2, dataset_version=1) is True

    # Verify hit
    payload_hit = await store.get_online_features(dataset, entity_id, track_stats=True)
    assert payload_hit is not None
    assert store.hits == 1
    assert payload_hit["values"] == fvals
    assert payload_hit["names"] == ["age", "balance"]
    assert payload_hit["version"] == 2

    # Cleanup
    await store.delete_online_features(dataset, entity_id)


@pytest.mark.asyncio
async def test_postgresql_fallback_and_repopulation():
    """
    Prove PostgreSQL fallback when an entity is missing in Redis,
    and verify automatic Redis repopulation.
    """
    store = OnlineFeatureStore()
    dataset_name = f"ff_test_fallback_ds_{uuid.uuid4().hex[:8]}"
    entity_id = f"customer_{uuid.uuid4().hex[:6]}"


    # Setup PostgreSQL offline feature store records
    async with AsyncSessionLocal() as session:
        ds_repo = DatasetRepository(session)
        feat_repo = FeatureRepository(session)
        fv_repo = FeatureValueRepository(session)

        ds = await ds_repo.create({
            "name": dataset_name,
            "description": "Test Fallback DS",
            "status": "ACTIVE"
        })

        feat1 = await feat_repo.create({
            "dataset_id": ds.id,
            "name": "credit_score",
            "dtype": "int64",
            "transformation": "Raw",
            "status": "ACTIVE"
        })
        feat2 = await feat_repo.create({
            "dataset_id": ds.id,
            "name": "tenure_months",
            "dtype": "int64",
            "transformation": "Raw",
            "status": "ACTIVE"
        })

        await fv_repo.create({
            "feature_id": feat1.id,
            "entity_id": entity_id,
            "value_json": 750,
            "version": 1,
            "status": "ACTIVE"
        })
        await fv_repo.create({
            "feature_id": feat2.id,
            "entity_id": entity_id,
            "value_json": 24,
            "version": 1,
            "status": "ACTIVE"
        })
        await session.commit()

    try:
        # Verify initial miss in Redis
        assert await store.get_online_features(dataset_name, entity_id, track_stats=False) is None

        # Execute fallback lookup
        payload, source = await store.get_online_features_with_fallback(dataset_name, entity_id)
        assert payload is not None
        assert source == "postgresql"
        assert payload["values"]["credit_score"] == 750
        assert payload["values"]["tenure_months"] == 24

        # Verify Redis repopulation: immediate subsequent lookup should hit Redis directly
        payload_hit, source_hit = await store.get_online_features_with_fallback(dataset_name, entity_id)
        assert payload_hit is not None
        assert source_hit == "redis"
        assert payload_hit["values"] == payload["values"]
    finally:
        await store.delete_online_features(dataset_name, entity_id)
        async with AsyncSessionLocal() as session:
            ds_repo = DatasetRepository(session)
            ds_to_del = await ds_repo.get_by_name(dataset_name)
            if ds_to_del:
                await ds_repo.delete(ds_to_del)
            await session.commit()


@pytest.mark.asyncio
async def test_ttl_expiration():
    """Prove configurable TTL expiration of online feature vectors."""
    store = OnlineFeatureStore()
    dataset = "ff_test:ttl"
    entity_id = "temp_user_99"

    # Pre-connect to ensure connection setup time does not consume TTL
    rc = await RedisClient.get_instance()
    await rc.connect()

    await store.store_online_features(dataset, entity_id, {"val": 123}, ttl=3)
    assert await store.get_online_features(dataset, entity_id, track_stats=False) is not None

    await asyncio.sleep(3.5)
    assert await store.get_online_features(dataset, entity_id, track_stats=False) is None




@pytest.mark.asyncio
async def test_batch_operations():
    """Prove batch feature writes and batch feature lookups across multiple entities."""
    store = OnlineFeatureStore()
    dataset = "ff_test:batch_ds"
    batch_map = {
        "ent_1": {"score": 10.0, "active": True},
        "ent_2": {"score": 20.0, "active": False},
        "ent_3": {"score": 30.0, "active": True}
    }

    write_results = await store.store_online_features_batch(dataset, batch_map, feature_version=1, ttl=30)
    assert all(write_results.values())
    assert len(write_results) == 3

    lookup_results = await store.get_online_features_batch(dataset, ["ent_1", "ent_2", "ent_missing"])
    assert lookup_results["ent_1"]["values"] == batch_map["ent_1"]
    assert lookup_results["ent_2"]["values"] == batch_map["ent_2"]
    assert lookup_results["ent_missing"] is None

    # Cleanup
    for eid in batch_map:
        await store.delete_online_features(dataset, eid)


@pytest.mark.asyncio
async def test_version_invalidation():
    """Prove automatic invalidation of outdated feature vectors after retraining."""
    store = OnlineFeatureStore()
    dataset = "ff_test:inval_ds"

    await store.store_online_features(dataset, "e1", {"feat_a": 1}, feature_version=1, ttl=60)
    await store.store_online_features(dataset, "e2", {"feat_a": 2}, feature_version=1, ttl=60)
    assert await store.get_online_features(dataset, "e1", track_stats=False) is not None

    # Invalidate all online features for the dataset
    deleted_count = await store.invalidate_dataset_features(dataset)
    assert deleted_count >= 2
    assert await store.get_online_features(dataset, "e1", track_stats=False) is None
    assert await store.get_online_features(dataset, "e2", track_stats=False) is None


@pytest.mark.asyncio
async def test_online_features_endpoints(client: AsyncClient):
    """Prove REST APIs for storing, batch storing, retrieving, refreshing, and deleting features."""
    dataset = "api_test_ds"
    entity_id = "api_entity_55"

    # 1. POST /api/v1/features/store
    store_payload = {
        "dataset": dataset,
        "entity_id": entity_id,
        "feature_values": {"f1": 100, "f2": "high"},
        "feature_version": 1,
        "dataset_version": 1,
        "ttl": 60
    }
    res_store = await client.post("/api/v1/features/store", json=store_payload)
    assert res_store.status_code == 200
    assert res_store.json() == {"status": "success", "stored": True, "entity_id": entity_id}

    # 2. GET /api/v1/features/{dataset}/{entity}
    res_get = await client.get(f"/api/v1/features/{dataset}/{entity_id}")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["values"] == {"f1": 100, "f2": "high"}
    assert data["names"] == ["f1", "f2"]

    # 3. POST /api/v1/features/store/batch
    batch_payload = {
        "dataset": dataset,
        "entity_features_map": {
            "batch_e1": {"val": 1},
            "batch_e2": {"val": 2}
        },
        "ttl": 30
    }
    res_batch = await client.post("/api/v1/features/store/batch", json=batch_payload)
    assert res_batch.status_code == 200
    assert res_batch.json()["results"]["batch_e1"] is True

    # 4. DELETE /api/v1/features/{dataset}/{entity}
    res_del = await client.delete(f"/api/v1/features/{dataset}/{entity_id}")
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True

    # Verify deleted via GET
    res_get_missing = await client.get(f"/api/v1/features/{dataset}/{entity_id}")
    assert res_get_missing.status_code == 404

    # Cleanup batch items
    await client.delete(f"/api/v1/features/{dataset}/batch_e1")
    await client.delete(f"/api/v1/features/{dataset}/batch_e2")
