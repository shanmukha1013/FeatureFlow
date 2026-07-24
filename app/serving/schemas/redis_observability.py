"""
Pydantic response schemas for Redis Enterprise Observability endpoints (`Phase 5`).

All fields are live — no hardcoded values. Credentials are always redacted.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class RedisMemorySchema(BaseModel):
    used_memory_bytes: int = Field(0, description="Used memory in bytes")
    used_memory_human: str = Field("0B", description="Used memory human-readable")
    used_memory_peak_bytes: int = Field(0, description="Peak memory in bytes")
    used_memory_peak_human: str = Field("0B", description="Peak memory human-readable")
    maxmemory_bytes: int = Field(0, description="Max memory limit (0 = unlimited)")
    maxmemory_human: str = Field("noeviction", description="Max memory human-readable")
    used_memory_pct: float = Field(0.0, description="Used memory as % of maxmemory")
    mem_fragmentation_ratio: float = Field(1.0, description="Memory fragmentation ratio")
    maxmemory_policy: str = Field("noeviction", description="Eviction policy")


class RedisKeyspaceSchema(BaseModel):
    total_keys: int = Field(0, description="Total keys across all databases")
    total_expires: int = Field(0, description="Total keys with TTL set")
    keyspace_hits: int = Field(0, description="Cache hits since server start")
    keyspace_misses: int = Field(0, description="Cache misses since server start")
    hit_ratio_pct: float = Field(0.0, description="Hit ratio percentage")
    expired_keys: int = Field(0, description="Total expired keys evicted")
    evicted_keys: int = Field(0, description="Total keys evicted due to maxmemory policy")


class RedisServerStatsSchema(BaseModel):
    total_commands_processed: int = 0
    total_connections_received: int = 0
    rejected_connections: int = 0
    instantaneous_ops_per_sec: int = 0
    total_net_input_bytes: int = 0
    total_net_output_bytes: int = 0


class RedisClientStatsSchema(BaseModel):
    connected_clients: int = 0
    blocked_clients: int = 0
    redis_version: str = "unknown"
    uptime_in_seconds: int = 0


class RedisConnectionPoolSchema(BaseModel):
    active: int = Field(0, description="Active connections in use")
    idle: int = Field(0, description="Idle connections available")
    total_created: int = Field(0, description="Total connections created")
    max: int = Field(0, description="Pool max size")
    utilization_pct: float = Field(0.0, description="Pool utilization %")
    available: bool = Field(True, description="Pool has available connections")


class RedisClientInternalStatsSchema(BaseModel):
    total_commands: int = 0
    total_errors: int = 0
    reconnect_count: int = 0
    last_error_at: Optional[str] = None
    last_connected_at: Optional[str] = None
    last_error_msg: Optional[str] = None


class RedisStatisticsResponse(BaseModel):
    """GET /api/v1/redis/statistics"""
    connection_status: str
    sampled_at: Optional[str] = None
    keyspace: RedisKeyspaceSchema = Field(default_factory=RedisKeyspaceSchema)
    server_stats: RedisServerStatsSchema = Field(default_factory=RedisServerStatsSchema)
    client_stats: Optional[RedisClientInternalStatsSchema] = None
    slow_log_count: int = 0
    sample_count: int = 0


class RedisHealthResponse(BaseModel):
    """GET /api/v1/redis/health"""
    connection_status: str
    ping_latency_ms: float = 0.0
    sampled_at: Optional[str] = None
    clients: RedisClientStatsSchema = Field(default_factory=RedisClientStatsSchema)
    pool: RedisConnectionPoolSchema = Field(default_factory=RedisConnectionPoolSchema)
    recovery: Dict[str, Any] = Field(default_factory=dict)
    monitor_running: bool = False


class LatencyStatsSchema(BaseModel):
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    min: float = 0.0
    max: float = 0.0
    avg: float = 0.0
    count: int = 0


class RedisPerformanceResponse(BaseModel):
    """GET /api/v1/redis/performance"""
    benchmark_id: Optional[str] = None
    iterations: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    single_get_ms: LatencyStatsSchema = Field(default_factory=LatencyStatsSchema)
    single_set_ms: LatencyStatsSchema = Field(default_factory=LatencyStatsSchema)
    batch_get_ms: LatencyStatsSchema = Field(default_factory=LatencyStatsSchema)
    pipeline_set_ms: LatencyStatsSchema = Field(default_factory=LatencyStatsSchema)
    online_feature_lookup_ms: LatencyStatsSchema = Field(default_factory=LatencyStatsSchema)
    model_cache_lookup_ms: LatencyStatsSchema = Field(default_factory=LatencyStatsSchema)
    prediction_cache_lookup_ms: LatencyStatsSchema = Field(default_factory=LatencyStatsSchema)
    errors: List[str] = Field(default_factory=list)
    message: str = "No benchmark has been run yet. POST /api/v1/redis/performance/run to execute."


class RedisConnectionsResponse(BaseModel):
    """GET /api/v1/redis/connections"""
    connection_status: str
    pool: RedisConnectionPoolSchema = Field(default_factory=RedisConnectionPoolSchema)
    clients: RedisClientStatsSchema = Field(default_factory=RedisClientStatsSchema)
    client_stats: RedisClientInternalStatsSchema = Field(default_factory=RedisClientInternalStatsSchema)
    recovery_status: Dict[str, Any] = Field(default_factory=dict)
    sampled_at: Optional[str] = None


class RedisMemoryResponse(BaseModel):
    """GET /api/v1/redis/memory"""
    connection_status: str
    memory: RedisMemorySchema = Field(default_factory=RedisMemorySchema)
    keyspace: RedisKeyspaceSchema = Field(default_factory=RedisKeyspaceSchema)
    sampled_at: Optional[str] = None
    alert_threshold_pct: float = 80.0
    alert_triggered: bool = False
