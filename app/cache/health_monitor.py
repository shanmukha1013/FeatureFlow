"""
Redis Health Monitor (`Phase 5`).

Continuously samples Redis server metrics in a background asyncio.Task and maintains
a live snapshot of memory, keyspace, client, latency, and pool telemetry.
Emits audit events when configured alert thresholds are exceeded.
"""
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class RedisHealthMonitor:
    """
    Singleton background monitor that periodically fetches live Redis server metrics
    and exposes them via `get_snapshot()`. Raises alerts to PostgreSQL audit log when:
      - Memory usage exceeds `redis_memory_alert_threshold`
      - Connection pool is exhausted
    """
    _instance: Optional["RedisHealthMonitor"] = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._snapshot: Dict[str, Any] = {}
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._sample_count: int = 0
        self._alert_count: int = 0
        self._initialized = True

    @classmethod
    async def get_instance(cls) -> "RedisHealthMonitor":
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Starts the background monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(), name="redis_health_monitor")
        logger.info("RedisHealthMonitor background task started.")

    async def stop(self) -> None:
        """Gracefully stops the background monitoring loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("RedisHealthMonitor background task stopped.")

    async def _monitor_loop(self) -> None:
        """Periodic sampling loop — runs every `redis_monitor_interval` seconds."""
        while self._running:
            try:
                await self._sample()
            except Exception as e:
                logger.debug(f"RedisHealthMonitor sample error: {e}")
            try:
                await asyncio.sleep(settings.redis_monitor_interval)
            except asyncio.CancelledError:
                break

    async def _sample(self) -> None:
        """Fetches a full metrics snapshot from Redis and checks alert thresholds."""
        from app.cache.redis_client import RedisClient
        client = await RedisClient.get_instance()

        snapshot: Dict[str, Any] = {
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "connection_status": "OFFLINE",
            "ping_latency_ms": 0.0,
            "memory": {},
            "keyspace": {},
            "clients": {},
            "stats": {},
            "pool": {},
            "slow_log_count": 0,
            "sample_count": self._sample_count + 1,
            "alert_count": self._alert_count,
        }

        if not client.is_connected:
            self._snapshot = snapshot
            return

        # Ping latency
        t0 = time.perf_counter()
        pinged = await client.ping()
        ping_ms = round((time.perf_counter() - t0) * 1000, 3)
        if not pinged:
            self._snapshot = snapshot
            return

        snapshot["connection_status"] = "ONLINE"
        snapshot["ping_latency_ms"] = ping_ms

        try:
            async def _info_all(c):
                info_mem = await c.info("memory")
                info_stats = await c.info("stats")
                info_clients = await c.info("clients")
                info_server = await c.info("server")
                info_keyspace = await c.info("keyspace")
                return info_mem, info_stats, info_clients, info_server, info_keyspace

            result = await client.execute_with_retry(_info_all)
            if result is None:
                self._snapshot = snapshot
                return

            info_mem, info_stats, info_clients, info_server, info_keyspace = result

            # --- Memory ---
            used_mem = int(info_mem.get("used_memory", 0))
            max_mem = int(info_mem.get("maxmemory", 0))
            used_pct = round((used_mem / max_mem * 100), 2) if max_mem > 0 else 0.0
            snapshot["memory"] = {
                "used_memory_bytes": used_mem,
                "used_memory_human": str(info_mem.get("used_memory_human", "0B")),
                "used_memory_peak_bytes": int(info_mem.get("used_memory_peak", 0)),
                "used_memory_peak_human": str(info_mem.get("used_memory_peak_human", "0B")),
                "maxmemory_bytes": max_mem,
                "maxmemory_human": str(info_mem.get("maxmemory_human", "noeviction")),
                "used_memory_pct": used_pct,
                "mem_fragmentation_ratio": float(info_mem.get("mem_fragmentation_ratio", 1.0)),
                "maxmemory_policy": str(info_mem.get("maxmemory_policy", "noeviction")),
            }

            # --- Stats / Keyspace ---
            hits = int(info_stats.get("keyspace_hits", 0))
            misses = int(info_stats.get("keyspace_misses", 0))
            total_kv = hits + misses
            hit_ratio = round((hits / total_kv * 100), 2) if total_kv > 0 else 0.0

            total_keys = sum(
                int(db_info.get("keys", 0))
                for db_info in info_keyspace.values()
                if isinstance(db_info, dict)
            )
            total_expires = sum(
                int(db_info.get("expires", 0))
                for db_info in info_keyspace.values()
                if isinstance(db_info, dict)
            )

            snapshot["keyspace"] = {
                "total_keys": total_keys,
                "total_expires": total_expires,
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "hit_ratio_pct": hit_ratio,
                "expired_keys": int(info_stats.get("expired_keys", 0)),
                "evicted_keys": int(info_stats.get("evicted_keys", 0)),
            }

            # --- Stats ---
            snapshot["stats"] = {
                "total_commands_processed": int(info_stats.get("total_commands_processed", 0)),
                "total_connections_received": int(info_stats.get("total_connections_received", 0)),
                "rejected_connections": int(info_stats.get("rejected_connections", 0)),
                "instantaneous_ops_per_sec": int(info_stats.get("instantaneous_ops_per_sec", 0)),
                "total_net_input_bytes": int(info_stats.get("total_net_input_bytes", 0)),
                "total_net_output_bytes": int(info_stats.get("total_net_output_bytes", 0)),
            }

            # --- Clients ---
            snapshot["clients"] = {
                "connected_clients": int(info_clients.get("connected_clients", 0)),
                "blocked_clients": int(info_clients.get("blocked_clients", 0)),
                "tracking_clients": int(info_clients.get("tracking_clients", 0)),
                "redis_version": str(info_server.get("redis_version", "unknown")),
                "uptime_in_seconds": int(info_server.get("uptime_in_seconds", 0)),
            }

            # --- Connection Pool ---
            snapshot["pool"] = client.connection_pool_stats

            # --- Slow Log ---
            try:
                async def _slowlog(c):
                    return await c.slowlog_len()
                slow_len = await client.execute_with_retry(_slowlog)
                snapshot["slow_log_count"] = int(slow_len or 0)
            except Exception:
                snapshot["slow_log_count"] = 0

            # --- Internal client counters ---
            snapshot["client_stats"] = {
                "total_commands": client.total_commands,
                "total_errors": client.total_errors,
                "reconnect_count": client.reconnect_count,
                "last_error_at": datetime.fromtimestamp(client.last_error_at, tz=timezone.utc).isoformat() if client.last_error_at else None,
                "last_connected_at": datetime.fromtimestamp(client.last_connected_at, tz=timezone.utc).isoformat() if client.last_connected_at else None,
                "last_error_msg": client.last_error_msg or None,
            }

            self._sample_count += 1
            snapshot["sample_count"] = self._sample_count
            self._snapshot = snapshot

            # --- Alert checks ---
            await self._check_alerts(snapshot)

        except Exception as e:
            logger.debug(f"Failed to collect Redis metrics: {e}")
            self._snapshot = snapshot

    async def _check_alerts(self, snapshot: Dict[str, Any]) -> None:
        """Emits audit events when thresholds are exceeded."""
        from app.storage.database import AsyncSessionLocal
        from app.monitoring.audit import AuditLogger, AuditEvent

        alerts = []

        # Memory alert
        used_pct = snapshot.get("memory", {}).get("used_memory_pct", 0.0)
        if used_pct > 0 and (used_pct / 100.0) >= settings.redis_memory_alert_threshold:
            alerts.append(AuditEvent(
                event_name="HIGH_MEMORY_USAGE",
                component="RedisHealthMonitor",
                severity="WARNING",
                payload={
                    "used_memory_pct": used_pct,
                    "threshold_pct": settings.redis_memory_alert_threshold * 100,
                    "used_memory_human": snapshot.get("memory", {}).get("used_memory_human", "?")
                }
            ))
            self._alert_count += 1

        # Pool exhaustion alert
        pool_stats = snapshot.get("pool", {})
        if pool_stats.get("active", 0) >= pool_stats.get("max", 1) and pool_stats.get("max", 0) > 0:
            alerts.append(AuditEvent(
                event_name="POOL_EXHAUSTED",
                component="RedisHealthMonitor",
                severity="ERROR",
                payload={"active": pool_stats.get("active"), "max": pool_stats.get("max")}
            ))
            self._alert_count += 1

        if alerts:
            try:
                async with AsyncSessionLocal() as session:
                    for event in alerts:
                        await AuditLogger.record(session, event)
                    await session.commit()
            except Exception as audit_e:
                logger.debug(f"Could not write monitor alert to audit log: {audit_e}")

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns the latest cached metrics snapshot (zero Redis calls)."""
        return dict(self._snapshot)

    def is_running(self) -> bool:
        return self._running and (self._task is not None) and not self._task.done()


async def get_health_monitor() -> RedisHealthMonitor:
    """Async singleton accessor for RedisHealthMonitor."""
    return await RedisHealthMonitor.get_instance()
