"""
Redis Auto-Recovery Manager (`Phase 5`).

Continuously probes Redis connectivity in a background asyncio.Task and:
  - Detects when Redis goes offline
  - Detects when Redis comes back online
  - Automatically warms all caches after reconnect
  - Emits REDIS_CONNECTED / REDIS_DISCONNECTED / REDIS_RECONNECTED / CACHE_WARMED / CACHE_RESTORED
    audit events to PostgreSQL
  - Never restarts FastAPI — recovery is fully transparent
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class RedisRecoveryManager:
    """
    Singleton recovery manager. Probes Redis every `redis_recovery_probe_interval` seconds.
    On outage detection and subsequent recovery, automatically re-warms all cache layers
    and persists audit events to PostgreSQL.
    """
    _instance: Optional["RedisRecoveryManager"] = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._was_connected: bool = True  # optimistic initial state
        self._recovery_count: int = 0
        self._outage_count: int = 0
        self._last_recovery_at: Optional[str] = None
        self._last_outage_at: Optional[str] = None
        self._cache_warm_count: int = 0
        self._initialized = True

    @classmethod
    async def get_instance(cls) -> "RedisRecoveryManager":
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Starts the background recovery probe loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._probe_loop(), name="redis_recovery_manager")
        logger.info("RedisRecoveryManager background probe started.")

    async def stop(self) -> None:
        """Gracefully stops the probe loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("RedisRecoveryManager background probe stopped.")

    async def _probe_loop(self) -> None:
        """Runs probe every `redis_recovery_probe_interval` seconds."""
        while self._running:
            try:
                await self._probe()
            except Exception as e:
                logger.debug(f"RedisRecoveryManager probe error: {e}")
            try:
                await asyncio.sleep(settings.redis_recovery_probe_interval)
            except asyncio.CancelledError:
                break

    async def _probe(self) -> None:
        """Checks connectivity and triggers recovery if Redis just came back online."""
        from app.cache.redis_client import RedisClient
        client = await RedisClient.get_instance()

        is_now_connected = client.is_connected and await client.ping()

        if self._was_connected and not is_now_connected:
            # Transition: ONLINE → OFFLINE
            self._was_connected = False
            self._outage_count += 1
            self._last_outage_at = datetime.now(timezone.utc).isoformat()
            logger.warning("RedisRecoveryManager: Redis went OFFLINE.")
            await self._emit_audit("REDIS_DISCONNECTED", "WARNING", {
                "outage_count": self._outage_count,
                "timestamp": self._last_outage_at
            })

        elif not self._was_connected and is_now_connected:
            # Transition: OFFLINE → ONLINE
            self._was_connected = True
            self._recovery_count += 1
            self._last_recovery_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"RedisRecoveryManager: Redis RECOVERED (recovery #{self._recovery_count}).")
            await self._emit_audit("REDIS_RECONNECTED", "INFO", {
                "recovery_count": self._recovery_count,
                "reconnect_count": client.reconnect_count,
                "timestamp": self._last_recovery_at
            })
            # Warm all caches transparently
            await self.warm_caches_after_recovery()

        elif not is_now_connected:
            # Attempt to reconnect
            await client.connect()

    async def warm_caches_after_recovery(self) -> Dict[str, Any]:
        """
        Warms all Redis cache layers after Redis reconnects.
        Emits CACHE_WARMED / CACHE_RESTORED audit events.
        Returns a dict describing what was warmed.
        """
        result: Dict[str, Any] = {
            "model_cache": False,
            "prediction_cache": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 1. Model Registry Cache
        try:
            from app.cache.model_cache import get_model_registry_cache
            mcache = await get_model_registry_cache()
            refresh_res = await mcache.refresh_all_caches()
            result["model_cache"] = refresh_res.get("status") == "success" if isinstance(refresh_res, dict) else False
            result["model_cache_details"] = refresh_res
        except Exception as e:
            logger.warning(f"Model cache warm failed during recovery: {e}")
            result["model_cache_error"] = str(e)

        # 2. Prediction Cache warm
        try:
            from app.cache.prediction_cache import get_prediction_cache
            pcache = await get_prediction_cache()
            warm_res = await pcache.warm_cache()
            result["prediction_cache"] = warm_res.get("status") == "success" if isinstance(warm_res, dict) else False
            result["prediction_cache_details"] = warm_res
        except Exception as e:
            logger.warning(f"Prediction cache warm failed during recovery: {e}")
            result["prediction_cache_error"] = str(e)

        self._cache_warm_count += 1

        await self._emit_audit("CACHE_WARMED", "INFO", {
            "warm_count": self._cache_warm_count,
            "model_cache_warmed": result["model_cache"],
            "prediction_cache_warmed": result["prediction_cache"]
        })
        await self._emit_audit("CACHE_RESTORED", "INFO", {
            "recovery_count": self._recovery_count,
            "cache_warm_count": self._cache_warm_count
        })

        logger.info(f"Cache warm after recovery complete: {result}")
        return result

    async def _emit_audit(self, event_name: str, severity: str, payload: Dict[str, Any]) -> None:
        """Records a Redis lifecycle event to PostgreSQL audit log."""
        try:
            from app.storage.database import AsyncSessionLocal
            from app.monitoring.audit import AuditLogger, AuditEvent
            event = AuditEvent(
                event_name=event_name,
                component="RedisRecoveryManager",
                severity=severity,
                payload=payload
            )
            async with AsyncSessionLocal() as session:
                await AuditLogger.record(session, event)
                await session.commit()
        except Exception as e:
            logger.debug(f"Failed to emit audit event {event_name}: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Returns current recovery manager status metrics (zero Redis calls)."""
        return {
            "is_running": self._running,
            "is_connected": self._was_connected,
            "recovery_count": self._recovery_count,
            "outage_count": self._outage_count,
            "cache_warm_count": self._cache_warm_count,
            "last_recovery_at": self._last_recovery_at,
            "last_outage_at": self._last_outage_at,
        }


async def get_recovery_manager() -> RedisRecoveryManager:
    """Async singleton accessor for RedisRecoveryManager."""
    return await RedisRecoveryManager.get_instance()
