"""
Redis Performance Benchmark (`Phase 5`).

Measures real latency distributions (p50/p95/p99) for:
  - Single GET/SET
  - Batch MGET/pipeline SET
  - Online Feature Store lookup
  - Model Registry Cache lookup
  - Prediction Cache lookup

All test keys are cleaned up after each benchmark run.
"""
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

_BENCH_KEY_PREFIX = "_bench_"


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    idx = min(idx, len(sorted_v) - 1)
    return round(sorted_v[idx], 4)


def _latency_report(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0, "count": 0}
    return {
        "p50": _percentile(values, 50),
        "p95": _percentile(values, 95),
        "p99": _percentile(values, 99),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "avg": round(sum(values) / len(values), 4),
        "count": len(values),
    }


class RedisBenchmark:
    """
    Production performance benchmark suite for all Redis cache layers.
    Uses real Redis Cloud — zero mock implementations.
    """

    def __init__(self) -> None:
        self._last_report: Optional[Dict[str, Any]] = None

    async def run_full_benchmark(self, iterations: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes all benchmark scenarios and returns a full `BenchmarkReport`.
        Cleans up all test keys after completion.
        """
        n = iterations or settings.redis_benchmark_iterations
        bench_id = str(uuid.uuid4())[:8]
        prefix = f"{_BENCH_KEY_PREFIX}{bench_id}_"
        keys_to_cleanup: List[str] = []

        logger.info(f"Starting Redis benchmark (iterations={n}, id={bench_id}).")
        report: Dict[str, Any] = {
            "benchmark_id": bench_id,
            "iterations": n,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "results": {},
            "errors": []
        }

        from app.cache.redis_client import RedisClient
        redis = await RedisClient.get_instance()

        # --- 1. Single GET latency ---
        get_latencies: List[float] = []
        # Seed a known key
        seed_key = f"{prefix}get_seed"
        keys_to_cleanup.append(seed_key)
        try:
            async def _set_seed(c): return await c.set(seed_key, "benchmark_value", ex=120)
            await redis.execute_with_retry(_set_seed)

            for _ in range(n):
                t0 = time.perf_counter()
                async def _get(c): return await c.get(seed_key)
                await redis.execute_with_retry(_get)
                get_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            report["errors"].append(f"single_get: {e}")
        report["results"]["single_get_ms"] = _latency_report(get_latencies)

        # --- 2. Single SET latency ---
        set_latencies: List[float] = []
        set_key = f"{prefix}set_test"
        keys_to_cleanup.append(set_key)
        try:
            for i in range(n):
                t0 = time.perf_counter()
                async def _set(c, v=i): return await c.set(set_key, str(v), ex=120)
                await redis.execute_with_retry(_set)
                set_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            report["errors"].append(f"single_set: {e}")
        report["results"]["single_set_ms"] = _latency_report(set_latencies)

        # --- 3. Batch GET (MGET) latency ---
        mget_latencies: List[float] = []
        batch_size = min(10, n)
        mget_keys = [f"{prefix}mget_{i}" for i in range(batch_size)]
        keys_to_cleanup.extend(mget_keys)
        try:
            async def _seed_mget(c):
                pipe = c.pipeline(transaction=False)
                for k in mget_keys:
                    pipe.set(k, "v", ex=120)
                return await pipe.execute()
            await redis.execute_with_retry(_seed_mget)

            for _ in range(n):
                t0 = time.perf_counter()
                async def _mget(c): return await c.mget(*mget_keys)
                await redis.execute_with_retry(_mget)
                mget_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            report["errors"].append(f"batch_get: {e}")
        report["results"]["batch_get_ms"] = _latency_report(mget_latencies)

        # --- 4. Pipeline SET latency ---
        pipeline_latencies: List[float] = []
        pipeline_batch = min(10, n)
        try:
            for i in range(n):
                pipe_keys = [f"{prefix}pipe_{i}_{j}" for j in range(pipeline_batch)]
                keys_to_cleanup.extend(pipe_keys)
                t0 = time.perf_counter()

                async def _pipeline(c, ks=pipe_keys, idx=i):
                    pipe = c.pipeline(transaction=False)
                    for k in ks:
                        pipe.set(k, f"v_{idx}", ex=120)
                    return await pipe.execute()
                await redis.execute_with_retry(_pipeline)
                pipeline_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            report["errors"].append(f"pipeline_set: {e}")
        report["results"]["pipeline_set_ms"] = _latency_report(pipeline_latencies)

        # --- 5. Online Feature Store lookup latency ---
        feature_latencies: List[float] = []
        feature_entity = f"{prefix}entity_001"
        try:
            from app.cache.online_store import get_online_store
            store = get_online_store()
            await store.store_online_features(
                dataset=f"{prefix}ds",
                entity_id=feature_entity,
                feature_values={"feat_a": 1.0, "feat_b": 2.0},
                ttl=120
            )
            for _ in range(n):
                t0 = time.perf_counter()
                await store.get_online_features(f"{prefix}ds", feature_entity)
                feature_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            report["errors"].append(f"online_feature_lookup: {e}")
        report["results"]["online_feature_lookup_ms"] = _latency_report(feature_latencies)

        # --- 6. Model Cache lookup latency ---
        model_latencies: List[float] = []
        bench_model_id = f"{prefix}model_001"
        try:
            from app.cache.model_cache import get_model_registry_cache
            mcache = await get_model_registry_cache()
            await mcache.store_model({
                "id": bench_model_id,
                "name": "benchmark_model",
                "dataset_id": "bench_ds",
                "algorithm": "RandomForest",
                "metrics": {"accuracy": 0.95},
                "status": "ACTIVE",
                "version": 1
            })
            for _ in range(n):
                t0 = time.perf_counter()
                await mcache.get_model(bench_model_id)
                model_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            report["errors"].append(f"model_cache_lookup: {e}")
        report["results"]["model_cache_lookup_ms"] = _latency_report(model_latencies)

        # --- 7. Prediction Cache lookup latency ---
        pred_latencies: List[float] = []
        pred_model_id = f"{prefix}pred_model"
        pred_payload = {"feature_a": 1.5, "feature_b": 2.7}
        pred_response = {"prediction": 1, "probability": 0.92, "latency_ms": 5.0}
        try:
            from app.cache.prediction_cache import get_prediction_cache
            pcache = await get_prediction_cache()
            await pcache.store_prediction(pred_model_id, "v1", "1", pred_payload, pred_response, ttl=120)
            for _ in range(n):
                t0 = time.perf_counter()
                await pcache.get_prediction(pred_model_id, "v1", "1", pred_payload, track_stats=False)
                pred_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            report["errors"].append(f"prediction_cache_lookup: {e}")
        report["results"]["prediction_cache_lookup_ms"] = _latency_report(pred_latencies)

        # --- Cleanup ---
        try:
            unique_keys = list(set(keys_to_cleanup))
            if unique_keys:
                async def _cleanup(c):
                    await c.delete(*unique_keys)
                await redis.execute_with_retry(_cleanup)
            # Also clean up prediction cache key via pattern
            try:
                from app.cache.prediction_cache import get_prediction_cache
                pcache = await get_prediction_cache()
                await pcache.invalidate_cache(model_id=pred_model_id)
            except Exception:
                pass
            # Clean model cache bench key
            try:
                from app.cache.model_cache import get_model_registry_cache
                mcache = await get_model_registry_cache()
                await mcache.delete_model_cache(bench_model_id)
            except Exception:
                pass
        except Exception as cleanup_e:
            logger.debug(f"Benchmark cleanup error: {cleanup_e}")

        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._last_report = report
        logger.info(f"Redis benchmark completed (id={bench_id}).")
        return report

    def get_last_report(self) -> Optional[Dict[str, Any]]:
        """Returns the latest cached benchmark report (no Redis calls)."""
        return self._last_report


_benchmark_instance: Optional[RedisBenchmark] = None


def get_benchmark() -> RedisBenchmark:
    """Returns the singleton RedisBenchmark instance."""
    global _benchmark_instance
    if _benchmark_instance is None:
        _benchmark_instance = RedisBenchmark()
    return _benchmark_instance
