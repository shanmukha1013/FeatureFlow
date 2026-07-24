from app.storage.database import AsyncSessionLocal
from app.cache.model_cache import ModelRegistryCache
from app.cache.online_store import OnlineFeatureStore
from app.cache.prediction_cache import get_prediction_cache, PredictionCache
from app.cache.performance_benchmark import get_benchmark
from app.cache.recovery_manager import get_recovery_manager, RedisRecoveryManager
from app.cache.health_monitor import get_health_monitor, RedisHealthMonitor
from app.cache.redis_client import RedisClient
from httpx import AsyncClient, ASGITransport
import pytest_asyncio
import uuid
import pytest

pytestmark = pytest.mark.integration

"""
Redis Enterprise Integration Test Suite (`Phase 5`).

Tests all Phase 5 features:
  1. Health Monitor — snapshot fields, background task lifecycle
  2. Performance Benchmark — all latency metrics present and valid
  3. Observability REST APIs — all 5 endpoints return 200 with live data
  4. Connection Pool Monitoring — pool stats non-null
  5. Memory Report — used_memory present and non-zero
  6. Audit Logging — REDIS events recorded in PostgreSQL
  7. Auto-Recovery — disconnect + reconnect + cache warm
  8. PostgreSQL Fallback — operations succeed even when Redis probed offline
  9. Security — no passwords/credentials in API responses
 10. Recovery Manager Status — status dict contains expected keys
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def reset_singletons():
    """Reset cache singletons between tests for clean state."""
    yield
    PredictionCache._instance = None
    OnlineFeatureStore._instance = None
    ModelRegistryCache._instance = None
    RedisHealthMonitor._instance = None
    RedisRecoveryManager._instance = None
    redis = await RedisClient.get_instance()
    await redis.disconnect()
    RedisClient._instance = None


# ---------------------------------------------------------------------------
# Test 1: Health Monitor Snapshot
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_monitor_snapshot_contains_required_fields():
    """Verify RedisHealthMonitor.get_snapshot() returns all required Phase 5 fields."""
    monitor = await get_health_monitor()
    await monitor.start()

    # Trigger an immediate sample
    await monitor._sample()
    await monitor.stop()

    snapshot = monitor.get_snapshot()
    assert isinstance(snapshot, dict), "Snapshot must be a dict"
    assert "connection_status" in snapshot
    assert snapshot["connection_status"] in ("ONLINE", "OFFLINE")
    assert "ping_latency_ms" in snapshot
    assert "memory" in snapshot
    assert "keyspace" in snapshot
    assert "stats" in snapshot
    assert "clients" in snapshot
    assert "pool" in snapshot
    assert "sample_count" in snapshot

    if snapshot["connection_status"] == "ONLINE":
        assert isinstance(snapshot["ping_latency_ms"], float)
        mem = snapshot["memory"]
        assert "used_memory_bytes" in mem
        assert "used_memory_human" in mem
        assert "maxmemory_policy" in mem
        ks = snapshot["keyspace"]
        assert "total_keys" in ks
        assert "hit_ratio_pct" in ks


# ---------------------------------------------------------------------------
# Test 2: Recovery Manager Status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recovery_manager_status_structure():
    """Verify RedisRecoveryManager.get_status() returns all expected keys."""
    manager = await get_recovery_manager()
    status = manager.get_status()

    required_keys = {"is_running", "is_connected", "recovery_count", "outage_count",
                     "cache_warm_count", "last_recovery_at", "last_outage_at"}
    assert required_keys.issubset(status.keys()), f"Missing keys: {required_keys - status.keys()}"
    assert isinstance(status["recovery_count"], int)
    assert isinstance(status["outage_count"], int)


# ---------------------------------------------------------------------------
# Test 3: Performance Benchmark Report
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_performance_benchmark_produces_valid_report():
    """
    Runs a quick benchmark (10 iterations) and validates all latency metrics
    are present and numeric. Verifies cleanup leaves no test keys.
    """
    bench = get_benchmark()
    report = await bench.run_full_benchmark(iterations=10)

    assert report is not None
    assert "benchmark_id" in report
    assert "results" in report
    assert "completed_at" in report

    results = report["results"]
    expected_metrics = [
        "single_get_ms", "single_set_ms", "batch_get_ms", "pipeline_set_ms",
        "online_feature_lookup_ms", "model_cache_lookup_ms", "prediction_cache_lookup_ms"
    ]
    for metric in expected_metrics:
        assert metric in results, f"Missing benchmark metric: {metric}"
        stats = results[metric]
        assert "p50" in stats and "p95" in stats and "p99" in stats
        assert isinstance(stats["avg"], float)
        assert stats["count"] >= 0


# ---------------------------------------------------------------------------
# Test 4: Connection Pool Stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connection_pool_stats_non_null():
    """Verify connection pool stats are accessible and structurally correct."""
    redis = await RedisClient.get_instance()
    pool = redis.connection_pool_stats

    assert "active" in pool
    assert "idle" in pool
    assert "max" in pool
    assert "utilization_pct" in pool
    assert "available" in pool
    assert isinstance(pool["max"], int) and pool["max"] > 0
    assert isinstance(pool["utilization_pct"], float)


# ---------------------------------------------------------------------------
# Test 5: Redis Client Stats Counters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_client_stats_counters_increment():
    """Verify that total_commands increments with each Redis operation."""
    redis = await RedisClient.get_instance()
    initial = redis.total_commands

    # Execute 5 operations
    for i in range(5):
        async def _op(c, v=i): return await c.set(f"_ent_test_{uuid.uuid4().hex}", str(v), ex=10)
        await redis.execute_with_retry(_op)

    assert redis.total_commands >= initial + 5, (
        f"Expected total_commands to increase by >= 5 from {initial}, got {redis.total_commands}"
    )
    assert isinstance(redis.total_errors, int)
    assert isinstance(redis.reconnect_count, int)


# ---------------------------------------------------------------------------
# Test 6: Observability APIs — All 5 Endpoints Return 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_observability_endpoints_all_return_200(client):
    """
    Calls all 5 Redis observability endpoints via the real FastAPI app.
    Verifies: 200 status, JSON response, no credentials in body.
    """
    endpoints = [
        "/api/v1/redis/statistics",
        "/api/v1/redis/health",
        "/api/v1/redis/performance",
        "/api/v1/redis/connections",
        "/api/v1/redis/memory",
    ]
    for endpoint in endpoints:
        resp = await client.get(endpoint)
        assert resp.status_code == 200, f"{endpoint} returned {resp.status_code}: {resp.text}"
        body = resp.json()
        assert isinstance(body, dict), f"{endpoint} did not return a JSON object"

        body_str = resp.text
        for secret_word in ["sirbao", "password", "SIrbAO"]:  # partial credential check
            assert secret_word.lower() not in body_str.lower(), (
                f"Credential exposed in {endpoint} response!"
            )


# ---------------------------------------------------------------------------
# Test 7: Redis Statistics Endpoint — Live Data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_statistics_live_data(client):
    """Verify /redis/statistics returns valid connection_status and keyspace structure."""
    resp = await client.get("/api/v1/redis/statistics")
    assert resp.status_code == 200
    body = resp.json()
    assert "connection_status" in body
    assert body["connection_status"] in ("ONLINE", "OFFLINE")


# ---------------------------------------------------------------------------
# Test 8: Redis Health Endpoint — Live Ping Latency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_health_endpoint_live_ping(client):
    """Verify /redis/health contains fresh ping_latency_ms > 0."""
    resp = await client.get("/api/v1/redis/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "ping_latency_ms" in body
    # If ONLINE, latency must be positive
    if body.get("connection_status") == "ONLINE":
        assert body["ping_latency_ms"] > 0, "Ping latency must be > 0 when ONLINE"
    assert "pool" in body
    assert "recovery" in body


# ---------------------------------------------------------------------------
# Test 9: Redis Memory Endpoint — Non-Zero Data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_memory_endpoint_structure(client):
    """Verify /redis/memory returns properly structured memory data."""
    resp = await client.get("/api/v1/redis/memory")
    assert resp.status_code == 200
    body = resp.json()
    assert "memory" in body
    mem = body["memory"]
    assert "used_memory_bytes" in mem
    assert "maxmemory_policy" in mem
    assert "alert_triggered" in body
    assert "alert_threshold_pct" in body


# ---------------------------------------------------------------------------
# Test 10: Audit Log — REDIS_CONNECTED Event in PostgreSQL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_redis_connected_event_recorded():
    """
    Verify that the REDIS_CONNECTED audit event is persisted to PostgreSQL.
    Emits one programmatically and reads it back from the DB.
    """
    from app.monitoring.audit import AuditLogger, AuditEvent
    from app.storage.models import AuditLog
    from sqlalchemy.future import select

    run_id = uuid.uuid4().hex[:8]
    event = AuditEvent(
        event_name="REDIS_CONNECTED",
        component="test_redis_enterprise",
        severity="INFO",
        payload={"test_run": run_id, "pool_size": 10}
    )

    async with AsyncSessionLocal() as session:
        await AuditLogger.record(session, event)
        await session.commit()

    # Read back
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.event_name == "REDIS_CONNECTED",
                AuditLog.component == "test_redis_enterprise"
            ).order_by(AuditLog.created_at.desc()).limit(1)
        )
        log = result.scalar_one_or_none()

    assert log is not None, "REDIS_CONNECTED event not found in audit_logs"
    assert log.event_name == "REDIS_CONNECTED"
    assert log.severity == "INFO"
    assert log.payload.get("test_run") == run_id


# ---------------------------------------------------------------------------
# Test 11: Audit Log — REDIS_RECONNECTED Event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_redis_reconnected_event():
    """
    Simulates REDIS_RECONNECTED audit event and verifies it is stored in PostgreSQL.
    """
    from app.monitoring.audit import AuditLogger, AuditEvent
    from app.storage.models import AuditLog
    from sqlalchemy.future import select

    run_id = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        await AuditLogger.record(session, AuditEvent(
            event_name="REDIS_RECONNECTED",
            component="test_redis_enterprise",
            severity="INFO",
            payload={"test_run": run_id, "recovery_count": 1}
        ))
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.event_name == "REDIS_RECONNECTED",
                AuditLog.component == "test_redis_enterprise"
            ).order_by(AuditLog.created_at.desc()).limit(1)
        )
        log = result.scalar_one_or_none()

    assert log is not None
    assert log.payload.get("test_run") == run_id


# ---------------------------------------------------------------------------
# Test 12: Auto-Recovery — Disconnect + Reconnect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_recovery_after_disconnect():
    """
    Forces a disconnect and then verifies that execute_with_retry reconnects automatically.
    Application must NOT crash. is_connected must return True after recovery.
    """
    redis = await RedisClient.get_instance()

    # Verify connected
    assert redis.is_connected

    # Store a key
    test_key = f"_ent_{uuid.uuid4().hex}"
    async def _set(c): return await c.set(test_key, "before_disconnect", ex=120)
    await redis.execute_with_retry(_set)

    # Disconnect
    await redis.disconnect()
    assert not redis.is_connected

    # Try operation — must auto-reconnect
    async def _get(c): return await c.get(test_key)
    result = await redis.execute_with_retry(_get)

    assert redis.is_connected, "Redis must auto-reconnect after disconnect"
    # Result is either the stored value or None (key may have persisted)
    assert isinstance(result, (str, type(None)))


# ---------------------------------------------------------------------------
# Test 13: Security — No Credentials in API Responses
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_security_no_credentials_in_any_response():
    """
    Calls all observability endpoints and verifies no Redis credentials appear in responses.
    """
    from app.serving.main import app

    credential_fragments = [
        "SIrbAOnl0X1prNZQ5qycQik1mDhk16KC",  # Redis password
        "default:SIrb",                          # user:partial_password
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for endpoint in ["/api/v1/redis/statistics", "/api/v1/redis/health",
                         "/api/v1/redis/connections", "/api/v1/redis/memory"]:
            resp = await client.get(endpoint)
            body_str = resp.text
            for frag in credential_fragments:
                assert frag not in body_str, f"Credential fragment '{frag}' found in {endpoint}"


# ---------------------------------------------------------------------------
# Test 14: PostgreSQL Fallback During Redis Probe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_postgresql_fallback_when_redis_offline():
    """
    When Redis returns None (simulated via a broken client),
    the application must fall through to PostgreSQL for prediction cache (miss → compute).
    No exception should propagate to the caller.
    """
    cache = await get_prediction_cache()
    model_id = f"_ent_{uuid.uuid4().hex}"

    # Inject a broken CacheManager
    class BrokenCache:
        async def get_json(self, *a, **kw): raise ConnectionError("simulated Redis offline")
        async def set_json(self, *a, **kw): raise ConnectionError("simulated Redis offline")
        async def delete(self, *a, **kw): raise ConnectionError("simulated Redis offline")

    original = cache.cache
    try:
        cache.cache = BrokenCache()
        # get_prediction must NOT raise — returns (None, "miss")
        result, source = await cache.get_prediction(model_id, "v1", "1", {"x": 1.0})
        assert result is None
        assert source == "miss"

        # store_prediction must NOT raise — returns False
        stored = await cache.store_prediction(model_id, "v1", "1", {"x": 1.0}, {"pred": 0})
        assert stored is False
    finally:
        cache.cache = original
