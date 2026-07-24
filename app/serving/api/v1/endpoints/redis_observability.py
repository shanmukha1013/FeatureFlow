"""
Redis Enterprise Observability REST Endpoints (`Phase 5`).

Exposes live Redis metrics with zero hardcoded values.
All credential references are redacted.

Routes:
  GET /redis/statistics   — Keyspace, command counts, hit/miss ratio, slow log
  GET /redis/health       — Full health with ping latency, client info, recovery state
  GET /redis/performance  — Latest benchmark report (or runs a quick probe benchmark)
  GET /redis/connections  — Connection pool utilization, internal client counters
  GET /redis/memory       — Memory usage, fragmentation, eviction policy, alerts
  POST /redis/performance/run  — Trigger a fresh benchmark run
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone

from app.serving.schemas.redis_observability import (
    RedisStatisticsResponse,
    RedisHealthResponse,
    RedisPerformanceResponse,
    RedisConnectionsResponse,
    RedisMemoryResponse,
    RedisKeyspaceSchema,
    RedisServerStatsSchema,
    RedisClientStatsSchema,
    RedisConnectionPoolSchema,
    RedisClientInternalStatsSchema,
    RedisMemorySchema,
    LatencyStatsSchema,
)
from app.config import settings
from app.utils.logger import get_logger

router = APIRouter(prefix="/redis", tags=["redis_observability"])
logger = get_logger(__name__)


@router.get("/statistics", response_model=RedisStatisticsResponse)
async def get_redis_statistics():
    """
    Returns live Redis keyspace statistics, command counts, hit/miss ratios, and slow log count.
    Data sourced from RedisHealthMonitor's latest snapshot + live Redis INFO fallback.
    """
    from app.cache.health_monitor import get_health_monitor

    monitor = await get_health_monitor()
    snapshot = monitor.get_snapshot()

    if not snapshot:
        # Fallback: direct live probe
        from app.cache.redis_client import RedisClient
        redis = await RedisClient.get_instance()
        health = await redis.health_check()
        return RedisStatisticsResponse(
            connection_status=health.get("connection_status", "OFFLINE"),
            sampled_at=datetime.now(timezone.utc).isoformat()
        )

    keyspace_data = snapshot.get("keyspace", {})
    stats_data = snapshot.get("stats", {})
    client_data = snapshot.get("client_stats", {})

    return RedisStatisticsResponse(
        connection_status=snapshot.get("connection_status", "OFFLINE"),
        sampled_at=snapshot.get("sampled_at"),
        keyspace=RedisKeyspaceSchema(
            total_keys=keyspace_data.get("total_keys", 0),
            total_expires=keyspace_data.get("total_expires", 0),
            keyspace_hits=keyspace_data.get("keyspace_hits", 0),
            keyspace_misses=keyspace_data.get("keyspace_misses", 0),
            hit_ratio_pct=keyspace_data.get("hit_ratio_pct", 0.0),
            expired_keys=keyspace_data.get("expired_keys", 0),
            evicted_keys=keyspace_data.get("evicted_keys", 0),
        ),
        server_stats=RedisServerStatsSchema(
            total_commands_processed=stats_data.get("total_commands_processed", 0),
            total_connections_received=stats_data.get("total_connections_received", 0),
            rejected_connections=stats_data.get("rejected_connections", 0),
            instantaneous_ops_per_sec=stats_data.get("instantaneous_ops_per_sec", 0),
            total_net_input_bytes=stats_data.get("total_net_input_bytes", 0),
            total_net_output_bytes=stats_data.get("total_net_output_bytes", 0),
        ),
        client_stats=RedisClientInternalStatsSchema(
            total_commands=client_data.get("total_commands", 0),
            total_errors=client_data.get("total_errors", 0),
            reconnect_count=client_data.get("reconnect_count", 0),
            last_error_at=client_data.get("last_error_at"),
            last_connected_at=client_data.get("last_connected_at"),
            last_error_msg=client_data.get("last_error_msg"),
        ) if client_data else None,
        slow_log_count=snapshot.get("slow_log_count", 0),
        sample_count=snapshot.get("sample_count", 0),
    )


@router.get("/health", response_model=RedisHealthResponse)
async def get_redis_health():
    """
    Returns comprehensive Redis health: ping latency, client count, pool utilization, recovery state.
    Triggers a live ping to always return fresh latency data.
    """
    from app.cache.redis_client import RedisClient
    from app.cache.health_monitor import get_health_monitor
    from app.cache.recovery_manager import get_recovery_manager
    import time

    redis = await RedisClient.get_instance()
    monitor = await get_health_monitor()
    recovery = await get_recovery_manager()

    snapshot = monitor.get_snapshot()
    recovery_status = recovery.get_status()
    pool_stats = redis.connection_pool_stats

    # Live ping
    t0 = time.perf_counter()
    pinged = await redis.ping()
    ping_ms = round((time.perf_counter() - t0) * 1000, 3)
    status = "ONLINE" if pinged else "OFFLINE"

    clients_data = snapshot.get("clients", {}) if snapshot else {}

    return RedisHealthResponse(
        connection_status=status,
        ping_latency_ms=ping_ms,
        sampled_at=datetime.now(timezone.utc).isoformat(),
        clients=RedisClientStatsSchema(
            connected_clients=clients_data.get("connected_clients", 0),
            blocked_clients=clients_data.get("blocked_clients", 0),
            redis_version=clients_data.get("redis_version", "unknown"),
            uptime_in_seconds=clients_data.get("uptime_in_seconds", 0),
        ),
        pool=RedisConnectionPoolSchema(**pool_stats),
        recovery=recovery_status,
        monitor_running=monitor.is_running(),
    )


@router.get("/performance", response_model=RedisPerformanceResponse)
async def get_redis_performance():
    """
    Returns the latest cached benchmark report.
    Run POST /redis/performance/run to trigger a fresh benchmark.
    """
    from app.cache.performance_benchmark import get_benchmark

    bench = get_benchmark()
    report = bench.get_last_report()

    if report is None:
        return RedisPerformanceResponse(
            message="No benchmark has been run yet. POST /api/v1/redis/performance/run to execute."
        )

    def _ls(key: str) -> LatencyStatsSchema:
        d = report.get("results", {}).get(key, {})
        return LatencyStatsSchema(**d) if d else LatencyStatsSchema()

    return RedisPerformanceResponse(
        benchmark_id=report.get("benchmark_id"),
        iterations=report.get("iterations", 0),
        started_at=report.get("started_at"),
        completed_at=report.get("completed_at"),
        single_get_ms=_ls("single_get_ms"),
        single_set_ms=_ls("single_set_ms"),
        batch_get_ms=_ls("batch_get_ms"),
        pipeline_set_ms=_ls("pipeline_set_ms"),
        online_feature_lookup_ms=_ls("online_feature_lookup_ms"),
        model_cache_lookup_ms=_ls("model_cache_lookup_ms"),
        prediction_cache_lookup_ms=_ls("prediction_cache_lookup_ms"),
        errors=report.get("errors", []),
        message="Benchmark completed successfully.",
    )


@router.post("/performance/run", response_model=RedisPerformanceResponse)
async def run_redis_benchmark(iterations: Optional[int] = Query(default=50, ge=10, le=500)):
    """
    Triggers a fresh Redis performance benchmark.
    Measures GET, SET, MGET, pipeline, Online Feature, Model Cache, and Prediction Cache latencies.
    """
    from app.cache.performance_benchmark import get_benchmark

    bench = get_benchmark()
    try:
        report = await bench.run_full_benchmark(iterations=iterations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {e}")

    def _ls(key: str) -> LatencyStatsSchema:
        d = report.get("results", {}).get(key, {})
        return LatencyStatsSchema(**d) if d else LatencyStatsSchema()

    return RedisPerformanceResponse(
        benchmark_id=report.get("benchmark_id"),
        iterations=report.get("iterations", 0),
        started_at=report.get("started_at"),
        completed_at=report.get("completed_at"),
        single_get_ms=_ls("single_get_ms"),
        single_set_ms=_ls("single_set_ms"),
        batch_get_ms=_ls("batch_get_ms"),
        pipeline_set_ms=_ls("pipeline_set_ms"),
        online_feature_lookup_ms=_ls("online_feature_lookup_ms"),
        model_cache_lookup_ms=_ls("model_cache_lookup_ms"),
        prediction_cache_lookup_ms=_ls("prediction_cache_lookup_ms"),
        errors=report.get("errors", []),
        message="Benchmark completed successfully.",
    )


@router.get("/connections", response_model=RedisConnectionsResponse)
async def get_redis_connections():
    """
    Returns live connection pool utilization, client counts, and recovery manager status.
    """
    from app.cache.redis_client import RedisClient
    from app.cache.health_monitor import get_health_monitor
    from app.cache.recovery_manager import get_recovery_manager

    redis = await RedisClient.get_instance()
    monitor = await get_health_monitor()
    recovery = await get_recovery_manager()

    snapshot = monitor.get_snapshot()
    pool_stats = redis.connection_pool_stats
    clients_data = snapshot.get("clients", {}) if snapshot else {}

    return RedisConnectionsResponse(
        connection_status="ONLINE" if redis.is_connected else "OFFLINE",
        pool=RedisConnectionPoolSchema(**pool_stats),
        clients=RedisClientStatsSchema(
            connected_clients=clients_data.get("connected_clients", 0),
            blocked_clients=clients_data.get("blocked_clients", 0),
            redis_version=clients_data.get("redis_version", "unknown"),
            uptime_in_seconds=clients_data.get("uptime_in_seconds", 0),
        ),
        client_stats=RedisClientInternalStatsSchema(
            total_commands=redis.total_commands,
            total_errors=redis.total_errors,
            reconnect_count=redis.reconnect_count,
            last_error_at=__import__("datetime").datetime.fromtimestamp(
                redis.last_error_at, tz=timezone.utc).isoformat() if redis.last_error_at else None,
            last_connected_at=__import__("datetime").datetime.fromtimestamp(
                redis.last_connected_at, tz=timezone.utc).isoformat() if redis.last_connected_at else None,
            last_error_msg=redis.last_error_msg or None,
        ),
        recovery_status=recovery.get_status(),
        sampled_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/memory", response_model=RedisMemoryResponse)
async def get_redis_memory():
    """
    Returns live Redis memory usage, peak, fragmentation, eviction policy, and alert status.
    """
    from app.cache.redis_client import RedisClient
    from app.cache.health_monitor import get_health_monitor

    redis = await RedisClient.get_instance()
    monitor = await get_health_monitor()

    snapshot = monitor.get_snapshot()
    mem_data = snapshot.get("memory", {}) if snapshot else {}
    keyspace_data = snapshot.get("keyspace", {}) if snapshot else {}

    if not mem_data:
        # Fallback: fetch live
        try:
            async def _info_mem(c):
                return await c.info("memory")
            raw = await redis.execute_with_retry(_info_mem)
            if raw:
                used = int(raw.get("used_memory", 0))
                peak = int(raw.get("used_memory_peak", 0))
                maxm = int(raw.get("maxmemory", 0))
                mem_data = {
                    "used_memory_bytes": used,
                    "used_memory_human": str(raw.get("used_memory_human", "0B")),
                    "used_memory_peak_bytes": peak,
                    "used_memory_peak_human": str(raw.get("used_memory_peak_human", "0B")),
                    "maxmemory_bytes": maxm,
                    "maxmemory_human": str(raw.get("maxmemory_human", "noeviction")),
                    "used_memory_pct": round((used / maxm * 100), 2) if maxm > 0 else 0.0,
                    "mem_fragmentation_ratio": float(raw.get("mem_fragmentation_ratio", 1.0)),
                    "maxmemory_policy": str(raw.get("maxmemory_policy", "noeviction")),
                }
        except Exception:
            pass

    alert_pct = settings.redis_memory_alert_threshold * 100
    used_pct = mem_data.get("used_memory_pct", 0.0)
    alert_triggered = used_pct >= alert_pct if used_pct > 0 else False

    return RedisMemoryResponse(
        connection_status="ONLINE" if redis.is_connected else "OFFLINE",
        memory=RedisMemorySchema(**mem_data) if mem_data else RedisMemorySchema(),
        keyspace=RedisKeyspaceSchema(
            total_keys=keyspace_data.get("total_keys", 0),
            total_expires=keyspace_data.get("total_expires", 0),
            keyspace_hits=keyspace_data.get("keyspace_hits", 0),
            keyspace_misses=keyspace_data.get("keyspace_misses", 0),
            hit_ratio_pct=keyspace_data.get("hit_ratio_pct", 0.0),
            expired_keys=keyspace_data.get("expired_keys", 0),
            evicted_keys=keyspace_data.get("evicted_keys", 0),
        ),
        sampled_at=snapshot.get("sampled_at") if snapshot else datetime.now(timezone.utc).isoformat(),
        alert_threshold_pct=alert_pct,
        alert_triggered=alert_triggered,
    )
