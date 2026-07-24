from app.cache.cache_manager import CacheManager
from app.cache.redis_client import RedisClient, sanitize_redis_url
from httpx import AsyncClient
import pytest_asyncio
import asyncio
import pytest

pytestmark = pytest.mark.integration

"""
Test suite for Redis Cloud Integration (Phase 1).

Verifies:
- Connection and singleton lifecycle
- Read, Write, Delete operations
- TTL expiration
- Automatic reconnection and resilience under failures
- Concurrent async access across pooled connections
- Health probe endpoint and credential redaction
"""


@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis_connections():
    """Ensure every test cleanly closes Redis connections before loop teardown."""
    yield
    client = await RedisClient.get_instance()
    await client.disconnect()


@pytest.mark.asyncio
async def test_redis_client_connection():
    """Verify singleton connection establishment and active ping health."""
    client = await RedisClient.get_instance()
    assert client.is_connected or await client.connect()
    assert await client.ping() is True


@pytest.mark.asyncio
async def test_redis_write_and_read():
    """Verify basic string write and read operations via CacheManager."""
    cache = CacheManager()
    key = "ff_test:write_read"
    value = "production_ready_value"

    assert await cache.set(key, value, ttl=60) is True
    retrieved = await cache.get(key)
    assert retrieved == value

    # Cleanup
    await cache.delete(key)


@pytest.mark.asyncio
async def test_redis_delete():
    """Verify key existence checking and deletion behavior."""
    cache = CacheManager()
    key = "ff_test:to_be_deleted"

    await cache.set(key, "temp", ttl=60)
    assert await cache.exists(key) is True

    deleted = await cache.delete(key)
    assert deleted is True
    assert await cache.exists(key) is False
    assert await cache.get(key) is None


@pytest.mark.asyncio
async def test_redis_ttl_expiration():
    """Verify key expiration when TTL expires."""
    cache = CacheManager()
    key = "ff_test:ttl_expire"

    await cache.set(key, "short_lived", ttl=3)
    assert await cache.exists(key) is True

    # Sleep slightly past TTL
    await asyncio.sleep(3.5)
    assert await cache.exists(key) is False


@pytest.mark.asyncio
async def test_redis_json_operations():
    """Verify structured dictionary serialization and deserialization via JSON."""
    cache = CacheManager()
    key = "ff_test:json_meta"
    payload = {"feature_id": "feat_123", "dataType": "FLOAT", "version": 2, "active": True}

    assert await cache.set_json(key, payload, ttl=60) is True
    loaded = await cache.get_json(key)
    assert loaded == payload

    # Test get_multi
    multi_res = await cache.get_multi([key, "ff_test:non_existent_key"])
    assert key in multi_res and multi_res[key] is not None
    assert "ff_test:non_existent_key" in multi_res and multi_res["ff_test:non_existent_key"] is None

    # Cleanup
    await cache.delete(key)


@pytest.mark.asyncio
async def test_redis_reconnection_and_resilience():
    """
    Verify automatic reconnect after client disconnect, and ensure connection
    failures gracefully return fallbacks without throwing unhandled exceptions.
    """
    client = await RedisClient.get_instance()

    # Simulate disconnect
    await client.disconnect()
    assert client.is_connected is False

    # Execute operation via CacheManager should auto-reconnect
    cache = CacheManager(client)
    key = "ff_test:reconnect"
    await cache.set(key, "recovered", ttl=30)
    assert await cache.get(key) == "recovered"
    await cache.delete(key)

    # Test graceful fallback with invalid URL (zero crashes allowed)
    bad_client = RedisClient(url="redis://invalid_host_domain_xyz:9999", pool_size=1, timeout=0.2)
    bad_cache = CacheManager(bad_client)

    # Operations should return None/False cleanly without raising
    assert await bad_cache.get("any_key") is None
    assert await bad_cache.set("any_key", "val") is False
    assert await bad_cache.exists("any_key") is False


@pytest.mark.asyncio
async def test_redis_concurrent_access():
    """Verify high-concurrency async operations do not starve pool or race."""
    cache = CacheManager()
    num_items = 10

    # Concurrent writes
    write_tasks = [cache.set(f"ff_test:conc:{i}", f"val_{i}", ttl=30) for i in range(num_items)]
    write_results = await asyncio.gather(*write_tasks)
    assert all(write_results)

    # Concurrent reads
    read_tasks = [cache.get(f"ff_test:conc:{i}") for i in range(num_items)]
    read_results = await asyncio.gather(*read_tasks)
    for i, res in enumerate(read_results):
        assert res == f"val_{i}"

    # Cleanup
    cleanup_tasks = [cache.delete(f"ff_test:conc:{i}") for i in range(num_items)]
    await asyncio.gather(*cleanup_tasks)


@pytest.mark.asyncio
async def test_redis_health_endpoint(client: AsyncClient):
    """Verify GET /health/redis health probe endpoint diagnostics and credential redaction."""
    response = await client.get("/health/redis")
    assert response.status_code == 200

    data = response.json()
    assert "connection_status" in data
    assert data["connection_status"] == "ONLINE"
    assert "ping_latency_ms" in data
    assert isinstance(data["ping_latency_ms"], float)
    assert "redis_version" in data
    assert "memory_usage" in data
    assert "connected_clients" in data
    assert "url_redacted" in data

    # Ensure credentials never leak in the endpoint output or url_redacted
    if data["url_redacted"]:
        assert "SIrbAOnl0X1prNZQ5qycQik1mDhk16KC" not in data["url_redacted"]
        from app.config import settings
        if "@" in settings.redis_url:
            assert "***@" in data["url_redacted"]


def test_sanitize_redis_url():
    """Verify sanitize_redis_url properly redacts sensitive password tokens."""
    raw_url = "redis://default:SIrbAOnl0X1prNZQ5qycQik1mDhk16KC@cup-calculator-relation-56972.db.redis.io:14389"
    sanitized = sanitize_redis_url(raw_url)
    assert "SIrbAOnl0X1prNZQ5qycQik1mDhk16KC" not in sanitized
    assert sanitized == "redis://***@cup-calculator-relation-56972.db.redis.io:14389"
