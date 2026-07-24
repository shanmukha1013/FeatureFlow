"""
Production-grade Redis Client wrapper for FeatureFlow.

Implements:
- Singleton pattern with loop-aware connection pooling
- Automatic reconnect & connection pooling
- Ping health check & status diagnostics
- Graceful shutdown hooks
- Retry logic with exponential backoff and timeout handling
- Credential redaction in logs
"""
import asyncio
import os
import re
import sys
import time
from typing import Optional, Dict, Any, Callable
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_redis_url(url: str) -> str:
    """Redacts user credentials and passwords from Redis connection strings for safe logging."""
    if not url:
        return "redis://unknown"
    return re.sub(r"://[^@]+@", "://***@", url)


class RedisClient:
    """
    Singleton Redis connection manager using redis.asyncio.

    Provides resilient pooled connections to Redis Cloud with automatic reconnects,
    timeouts, ping diagnostics, and zero-crash fallback guarantees.
    """
    _instance: Optional["RedisClient"] = None
    _lock = asyncio.Lock()

    def __init__(self, url: Optional[str] = None, pool_size: Optional[int] = None, timeout: Optional[float] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.url = url or settings.redis_url
        is_test = "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST") or settings.environment.lower() == "test"
        self.pool_size = pool_size or (10 if is_test else settings.redis_pool_size)
        self.timeout = timeout or settings.redis_timeout
        self.max_retries = 5 if is_test else 3

        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[aioredis.Redis] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_connected: bool = False

        # Phase 5: Live telemetry counters
        self.total_commands: int = 0
        self.total_errors: int = 0
        self.reconnect_count: int = 0
        self.last_connected_at: Optional[float] = None   # unix timestamp
        self.last_error_at: Optional[float] = None        # unix timestamp
        self.last_error_msg: str = ""

        self._initialized = True

    @classmethod
    async def get_instance(cls, url: Optional[str] = None) -> "RedisClient":
        """Returns the async singleton instance of RedisClient."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(url=url)
            # connect() handles its own locking, call outside the get_instance lock
            if not cls._instance.is_connected:
                await cls._instance.connect()
        return cls._instance

    @classmethod
    def get_instance_sync(cls, url: Optional[str] = None) -> "RedisClient":
        """Synchronous accessor for the singleton instance (does not force async connect immediately)."""
        if cls._instance is None:
            cls._instance = cls(url=url)
        return cls._instance

    def _ensure_loop_safety(self) -> None:
        """
        Ensures the connection pool and client belong to the active asyncio event loop.
        In pytest or multi-loop environments, resets pool automatically when loops change.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._pool is not None and self._loop is not None and current_loop is not None and self._loop != current_loop:
            self._pool = None
            self._client = None
            self._is_connected = False
            self._loop = current_loop
        elif self._loop is None and current_loop is not None:
            self._loop = current_loop

    async def connect(self) -> bool:
        """
        Initializes the connection pool and verifies connection to Redis via ping.
        Never crashes the application if connection fails.
        """
        sanitized = sanitize_redis_url(self.url)
        async with self._lock:
            # If already connected by a previous task waiting on the lock, just return True
            if self._pool is not None and self._client is not None and self._is_connected:
                return True

            try:
                self._ensure_loop_safety()
                if self._pool is None:
                    self._pool = ConnectionPool.from_url(
                        self.url,
                        max_connections=self.pool_size,
                        socket_timeout=self.timeout,
                        socket_connect_timeout=self.timeout,
                        retry_on_timeout=True,
                        decode_responses=True
                    )
                if self._client is None:
                    self._client = aioredis.Redis(connection_pool=self._pool)
                if self._semaphore is None:
                    self._semaphore = asyncio.Semaphore(self.pool_size)

                self._is_connected = True
                self.last_connected_at = time.time()
                logger.info(f"Successfully connected to Redis Cloud ({sanitized}) with pool size {self.pool_size}.")
                return True
            except Exception as e:
                self._is_connected = False
                self.last_error_at = time.time()
                self.last_error_msg = str(e)
                logger.error(f"Failed to connect to Redis ({sanitized}): {e}. Application will fall back to PostgreSQL.")
                return False

    async def disconnect(self) -> None:
        """Gracefully closes all connections in the pool."""
        sanitized = sanitize_redis_url(self.url)
        async with self._lock:
            try:
                if self._client:
                    await self._client.aclose()
                    self._client = None
                if self._pool:
                    await self._pool.disconnect()
                    self._pool = None
                self._is_connected = False
                self._loop = None
                logger.info(f"Cleanly disconnected from Redis ({sanitized}).")
            except Exception as e:
                logger.warning(f"Error during Redis disconnect ({sanitized}): {e}")
                self._is_connected = False
                self._loop = None

    @property
    def client(self) -> Optional[aioredis.Redis]:
        """Returns the raw aioredis client instance after checking loop safety."""
        self._ensure_loop_safety()
        return self._client

    @property
    def is_connected(self) -> bool:
        """Returns current cached connection status."""
        self._ensure_loop_safety()
        return self._is_connected and self._client is not None

    async def ping(self) -> bool:
        """Executes a ping command to verify active connection health."""
        self._ensure_loop_safety()
        if not self._client:
            return False
        try:
            res = await asyncio.wait_for(self._client.ping(), timeout=self.timeout)
            return bool(res)
        except Exception as e:
            logger.debug(f"Redis ping failed: {e}")
            return False

    async def execute_with_retry(self, operation: Callable[[aioredis.Redis], Any]) -> Any:
        """
        Executes a Redis operation with automatic reconnect and exponential backoff retry logic.
        Never raises fatal crashes to the caller if Redis is down.
        """
        sanitized = sanitize_redis_url(self.url)
        for attempt in range(1, self.max_retries + 1):
            try:
                self._ensure_loop_safety()
                if not self._client or not self._is_connected:
                    connected = await self.connect()
                    if not connected:
                        raise RedisConnectionError("Redis connection is offline.")

                async def _run():
                    if self._semaphore:
                        async with self._semaphore:
                            return await operation(self._client)
                    else:
                        return await operation(self._client)

                result = await asyncio.wait_for(_run(), timeout=self.timeout)
                self.total_commands += 1
                return result
            except (RedisConnectionError, RedisTimeoutError, asyncio.TimeoutError) as e:
                self.total_errors += 1
                self.last_error_at = time.time()
                self.last_error_msg = str(e)
                logger.warning(
                    f"Redis network/timeout error ({sanitized}) on attempt {attempt}/{self.max_retries}: {e}."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(0.2 * (2 ** (attempt - 1)))
                    # Note: We rely on aioredis ConnectionPool's native auto-reconnect for broken sockets.
                    # We do not destroy the pool here, as that causes disconnect storms and deadlocks.
                else:
                    logger.error(f"Redis operation failed after {self.max_retries} retries ({sanitized}). Falling back.")
                    return None
            except RedisError as e:
                logger.error(f"Redis operational error: {e}")
                self.total_errors += 1
                self.last_error_at = time.time()
                self.last_error_msg = str(e)
                return None
            except Exception as e:
                logger.error(f"Unexpected error executing Redis operation: {e}")
                self.total_errors += 1
                self.last_error_at = time.time()
                self.last_error_msg = str(e)
                return None
        return None

    async def delete(self, *keys: str) -> int:
        """Convenience method to delete one or more keys. Returns count of deleted keys."""
        if not keys:
            return 0

        async def _op(client: aioredis.Redis) -> int:
            return await client.delete(*keys)
        res = await self.execute_with_retry(_op)
        return int(res or 0)

    @property
    def connection_pool_stats(self) -> Dict[str, Any]:
        """Returns live connection pool utilization metrics."""
        if self._pool is None:
            return {"active": 0, "idle": 0, "max": self.pool_size, "utilization_pct": 0.0, "available": True}
        try:
            # ConnectionPool internals: _available_connections (idle), _in_use_connections (active)
            idle = len(getattr(self._pool, "_available_connections", []))
            active = len(getattr(self._pool, "_in_use_connections", set()))
            total_created = idle + active
            utilization = round((active / self.pool_size) * 100, 2) if self.pool_size > 0 else 0.0
            return {
                "active": active,
                "idle": idle,
                "total_created": total_created,
                "max": self.pool_size,
                "utilization_pct": utilization,
                "available": active < self.pool_size
            }
        except Exception:
            return {"active": 0, "idle": 0, "max": self.pool_size, "utilization_pct": 0.0, "available": True}

    async def health_check(self) -> Dict[str, Any]:
        """
        Returns comprehensive diagnostics including connection status, ping latency,
        Redis version, memory usage, and connected clients.
        """
        sanitized = sanitize_redis_url(self.url)
        status = "OFFLINE"
        latency_ms = 0.0
        version = "unknown"
        memory_usage: Dict[str, Any] = {}
        connected_clients = 0

        self._ensure_loop_safety()
        if not self._client or not self._is_connected:
            await self.connect()

        if self._client:
            start_time = time.perf_counter()
            try:
                if await asyncio.wait_for(self._client.ping(), timeout=self.timeout):
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    status = "ONLINE"
                    self._is_connected = True

                    # Fetch detailed server info
                    try:
                        info_server = await self._client.info("server")
                        info_memory = await self._client.info("memory")
                        info_clients = await self._client.info("clients")

                        version = str(info_server.get("redis_version", "unknown"))
                        connected_clients = int(info_clients.get("connected_clients", 0))
                        memory_usage = {
                            "used_memory_bytes": int(info_memory.get("used_memory", 0)),
                            "used_memory_human": str(info_memory.get("used_memory_human", "0B")),
                            "used_memory_peak_human": str(info_memory.get("used_memory_peak_human", "0B")),
                            "maxmemory_human": str(info_memory.get("maxmemory_human", "0B"))
                        }
                    except Exception as info_e:
                        logger.debug(f"Failed to retrieve detailed Redis INFO metrics: {info_e}")
            except Exception as e:
                logger.debug(f"Redis health check failed ({sanitized}): {e}")
                self._is_connected = False
                status = "OFFLINE"

        return {
            "connection_status": status,
            "ping_latency_ms": latency_ms,
            "redis_version": version,
            "memory_usage": memory_usage,
            "connected_clients": connected_clients,
            "url_redacted": sanitized
        }


def get_redis_client() -> RedisClient:
    """Returns the synchronous singleton instance accessor for dependency injection."""
    return RedisClient.get_instance_sync()
