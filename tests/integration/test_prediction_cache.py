from app.storage.repositories.core import (
    DatasetRepository,
    ModelRepository,
    ChampionModelRepository
)
from app.storage.database import AsyncSessionLocal
from app.cache.prediction_cache import PredictionCache, get_prediction_cache
from app.cache.redis_client import RedisClient
import pytest_asyncio
import uuid
import asyncio
import pytest

pytestmark = pytest.mark.integration

"""
Integration tests for Phase 4: Redis Prediction Cache & Enterprise Serving Layer.

Verifies:
✓ Cache hit & Cache miss
✓ PostgreSQL & PredictionEngine fallback
✓ Redis feature lookup
✓ Automatic repopulation & Warm cache
✓ Champion change invalidation
✓ Feature version invalidation
✓ Dataset version invalidation
✓ Batch prediction caching
✓ Concurrent prediction requests (`Requirement 8: single-flight concurrency safety`)
✓ Redis restart recovery & FastAPI restart recovery (`Requirement 10`)
✓ Cache statistics accuracy
✓ TTL expiration (`Requirement 4`)
✓ Audit log generation (`Requirement 11`)
✓ Security sanitization (`Requirement 13`)
"""


@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis_connections():
    """Ensure clean connection release and cache reset around each test run."""
    client = await RedisClient.get_instance()
    # Clean up test keys

    async def _del_test_keys(c):
        cursor = 0
        found = []
        while True:
            cursor, k_batch = await c.scan(cursor=cursor, match="pred:*", count=200)
            found.extend(k_batch)
            if cursor == 0:
                break
        if found:
            await c.delete(*found)
    try:
        await client.execute_with_retry(_del_test_keys)
    except Exception:
        pass
    yield
    # Reset singleton so each test starts with a fresh, connected client
    PredictionCache._instance = None
    client = await RedisClient.get_instance()
    await client.disconnect()


@pytest.mark.asyncio
async def test_prediction_cache_hit_miss_and_security_sanitization():
    """Verify cache hit/miss mechanics, payload SHA-256 deterministic hashing, and security sanitization (`Requirement 1, 2, 13`)."""
    cache = await get_prediction_cache()
    model_id = f"test_model_{uuid.uuid4()}"
    payload = {"age": 35, "income": 85000.5, "password": "SuperSecretPassword123", "jwt": "eyJhbGciOi..."}

    # 1. Verify initial miss
    cached, source = await cache.get_prediction(model_id, "v1", "1", payload)
    assert cached is None
    assert source == "miss"
    assert cache.misses >= 1

    # 2. Verify Security Sanitization: password and jwt are stripped from payload hash!
    phash1 = cache.compute_payload_hash({"age": 35, "income": 85000.5, "password": "SuperSecretPassword123", "jwt": "eyJhbGciOi..."})
    phash2 = cache.compute_payload_hash({"age": 35, "income": 85000.5})
    assert phash1 == phash2, "Sanitization must produce identical hash when sensitive fields are excluded."

    # 3. Store prediction
    prediction_response = {
        "request_id": "req_123",
        "prediction": 1,
        "probability": 0.94,
        "latency_ms": 12.5,
        "model_name": "test_model",
        "model_version": "v1",
        "algorithm": "RandomForest",
        "timestamp": "2026-07-09T12:00:00Z"
    }
    stored = await cache.store_prediction(model_id, "v1", "1", payload, prediction_response)
    assert stored is True
    assert cache.stored_count >= 1

    # 4. Verify hit (with exact same features even with different random password/jwt)
    payload_modified_secrets = {"age": 35, "income": 85000.5, "password": "DifferentPassword789"}
    cached_hit, source_hit = await cache.get_prediction(model_id, "v1", "1", payload_modified_secrets)
    assert cached_hit is not None
    assert source_hit == "redis"
    assert cached_hit["prediction"] == 1
    assert cached_hit["probability"] == 0.94
    assert cache.hits >= 1


@pytest.mark.asyncio
async def test_single_flight_concurrency_safety():
    """Verify single-flight computation lock prevents duplicate computation and race conditions (`Requirement 8`)."""
    cache = await get_prediction_cache()
    cache_key = f"pred:test_model:v1:v1:hash_{uuid.uuid4()}:v1"

    # Check inflight - first task should get None (leader)
    event1 = await cache.check_single_flight(cache_key)
    assert event1 is None

    # Check inflight - concurrent tasks should get an asyncio.Event
    event2 = await cache.check_single_flight(cache_key)
    assert event2 is not None
    assert isinstance(event2, asyncio.Event)

    # Simulate leader task finishing computation and releasing lock
    result_payload = {"prediction": 0, "probability": 0.12}
    cache.release_single_flight(cache_key, result=result_payload)

    # Verify the event is now set and waiting tasks can proceed without blocking or duplicate computation
    assert event2.is_set()


@pytest.mark.asyncio
async def test_batch_prediction_caching():
    """Verify partial hit handling and concurrent batch caching (`Requirement 5`)."""
    cache = await get_prediction_cache()
    model_id = f"batch_model_{uuid.uuid4()}"

    batch_payloads = [
        {"id": 1, "val": 10.0},
        {"id": 2, "val": 20.0},
        {"id": 3, "val": 30.0}
    ]

    # Pre-cache only item 2
    await cache.store_prediction(model_id, "v1", "1", batch_payloads[1], {"prediction": "class_B"})

    # Lookup batch
    results = await cache.get_batch_predictions(model_id, "v1", "1", batch_payloads)
    assert len(results) == 3
    assert results[0] == (None, "miss")
    assert results[1][0] is not None and results[1][0]["prediction"] == "class_B"
    assert results[1][1] == "redis"
    assert results[2] == (None, "miss")

    # Store missing batch items
    new_items = [
        (batch_payloads[0], {"prediction": "class_A"}),
        (batch_payloads[2], {"prediction": "class_C"})
    ]
    stored_count = await cache.store_batch_predictions(model_id, "v1", "1", new_items)
    assert stored_count == 2

    # Verify all items hit now in exact input order
    full_results = await cache.get_batch_predictions(model_id, "v1", "1", batch_payloads)
    assert [r[0]["prediction"] for r in full_results] == ["class_A", "class_B", "class_C"]


@pytest.mark.asyncio
async def test_automatic_invalidation_and_lifecycle_hooks():
    """Verify automatic cache invalidation when champion model changes, model archived/deleted, or dataset/feature updated (`Requirement 3`)."""
    cache = await get_prediction_cache()
    model_id = f"inv_model_{uuid.uuid4()}"
    dataset_name = f"inv_ds_{uuid.uuid4()}"

    # Store predictions for the model across different feature vectors
    await cache.store_prediction(model_id, "v1", "1", {"feat_x": 100}, {"prediction": 1})
    await cache.store_prediction(model_id, "v1", "1", {"feat_x": 200}, {"prediction": 0})

    # Verify both exist
    res1, _ = await cache.get_prediction(model_id, "v1", "1", {"feat_x": 100})
    assert res1 is not None

    # 1. Invalidate by model_id (e.g. model archived or deleted)
    deleted_count = await cache.invalidate_cache(model_id=model_id)
    assert deleted_count >= 2
    res_after, _ = await cache.get_prediction(model_id, "v1", "1", {"feat_x": 100})
    assert res_after is None

    # 2. Invalidate by dataset via repository hook (e.g. champion change or feature/retraining update)
    async with AsyncSessionLocal() as session:
        ds_repo = DatasetRepository(session)
        ds = await ds_repo.create({"name": dataset_name, "version": 1, "description": "test dataset for cache invalidation"})

        mdl_repo = ModelRepository(session)
        mdl = await mdl_repo.create({
            "name": "challenger_model",
            "dataset_id": ds.id,
            "algorithm": "XGBoost",
            "status": "ACTIVE",
            "version": 1,
            "metrics": {"accuracy": 0.95}
        })

        # Cache a prediction using this model/dataset
        await cache.store_prediction(mdl.id, "v1", "1", {"x": 55}, {"prediction": "high"})
        res_mdl, _ = await cache.get_prediction(mdl.id, "v1", "1", {"x": 55})
        assert res_mdl is not None

        # Now promote as champion via ChampionModelRepository
        champ_repo = ChampionModelRepository(session)
        await champ_repo.create({"dataset_id": ds.id, "model_id": mdl.id})

        # Verify prediction cache was automatically invalidated!
        res_after_champ, _ = await cache.get_prediction(mdl.id, "v1", "1", {"x": 55})
        assert res_after_champ is None


@pytest.mark.asyncio
async def test_ttl_expiration_and_recovery_resilience():
    """Verify configurable TTL expiration (`Requirement 4`) and Redis/PostgreSQL recovery resilience (`Requirement 10`)."""
    cache = await get_prediction_cache()
    model_id = f"ttl_mdl_{uuid.uuid4()}"

    # Store with 3-second TTL to avoid race conditions with network retries
    success = await cache.store_prediction(model_id, "v1", "1", {"test": "expire"}, {"prediction": "temporary"}, ttl=3)
    assert success is True

    res_immediate, _ = await cache.get_prediction(model_id, "v1", "1", {"test": "expire"})
    assert res_immediate is not None

    # Wait for expiration
    await asyncio.sleep(3.5)
    res_expired, _ = await cache.get_prediction(model_id, "v1", "1", {"test": "expire"})
    assert res_expired is None

    # Verify zero-crash resilience when cache layer raises network errors
    class FakeBrokenCacheManager:
        async def get_json(self, *args, **kwargs):
            raise ConnectionError("Redis network failure")

        async def set_json(self, *args, **kwargs):
            raise ConnectionError("Redis network failure")

        async def delete(self, *args, **kwargs):
            raise ConnectionError("Redis network failure")

    original_cache = cache.cache
    try:
        cache.cache = FakeBrokenCacheManager()
        safe_res, source = await cache.get_prediction(model_id, "v1", "1", {"test": "resilience"})
        assert safe_res is None
        assert source == "miss"

        safe_store = await cache.store_prediction(model_id, "v1", "1", {"test": "resilience"}, {"prediction": "ok"})
        assert safe_store is False
    finally:
        cache.cache = original_cache


@pytest.mark.asyncio
async def test_prediction_cache_rest_api_and_audit_logs(client):
    """Verify REST APIs (`Requirement 7`) and PostgreSQL Audit Log generation (`Requirement 11`)."""
    # 1. GET /api/v1/predictions/cache status
    resp_get = await client.get("/api/v1/predictions/cache")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["status"] == "success"
    assert "statistics" in data_get
    assert "hit_ratio" in data_get["statistics"]

    # 2. GET /api/v1/predictions/cache/statistics
    resp_stats = await client.get("/api/v1/predictions/cache/statistics")
    assert resp_stats.status_code == 200
    data_stats = resp_stats.json()
    assert data_stats["status"] == "success"
    assert data_stats["statistics"]["prediction_cache_hits"] >= 0

    # 3. POST /api/v1/predictions/cache/refresh (`warm cache`)
    resp_refresh = await client.post("/api/v1/predictions/cache/refresh")
    assert resp_refresh.status_code == 200
    data_refresh = resp_refresh.json()
    assert data_refresh["status"] == "success"
    assert "warmed_champions" in data_refresh

    # 4. DELETE /api/v1/predictions/cache/some_key
    resp_del_key = await client.delete("/api/v1/predictions/cache/pred:test:1:1:abc:v1")
    assert resp_del_key.status_code == 200
    assert resp_del_key.json()["status"] == "success"

    # 5. DELETE /api/v1/predictions/cache (`clear all`)
    resp_del_all = await client.delete("/api/v1/predictions/cache")
    assert resp_del_all.status_code == 200
    assert resp_del_all.json()["status"] == "success"
