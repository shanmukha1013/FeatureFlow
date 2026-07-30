import asyncio

import psutil

from app.observability.metrics import (
    cache_hits_total,
    cache_misses_total,
    datasets_registered_total,
    drift_checks_total,
    drift_detected_total,
    mlflow_experiments_created_total,
    mlflow_models_promoted_total,
    mlflow_models_registered_total,
    prediction_failures_total,
    prediction_latency_seconds,
    prediction_requests_total,
    process_cpu_percent,
    process_memory_bytes,
    training_duration_seconds,
    training_failures_total,
    training_runs_total,
)


# --- Prediction Instrumentation ---
def record_prediction(model_name: str, latency: float):
    prediction_requests_total.labels(model_name=model_name).inc()
    prediction_latency_seconds.labels(model_name=model_name).observe(latency)


def record_prediction_failure(model_name: str, reason: str):
    prediction_failures_total.labels(model_name=model_name, reason=reason).inc()


# --- Training Instrumentation ---
def record_training_success(algorithm: str, duration: float):
    training_runs_total.labels(algorithm=algorithm).inc()
    training_duration_seconds.labels(algorithm=algorithm).observe(duration)


def record_training_failure(algorithm: str):
    training_failures_total.labels(algorithm=algorithm).inc()


# --- MLflow Instrumentation ---
def record_mlflow_experiment_created():
    mlflow_experiments_created_total.inc()


def record_mlflow_model_registered():
    mlflow_models_registered_total.inc()


def record_mlflow_model_promoted(alias: str):
    mlflow_models_promoted_total.labels(alias=alias).inc()


# --- Monitoring/Drift Instrumentation ---
def record_drift_check(drift_detected: bool):
    drift_checks_total.inc()
    if drift_detected:
        drift_detected_total.inc()


# --- Caching Instrumentation ---
def record_cache_hit(cache_type: str):
    cache_hits_total.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str):
    cache_misses_total.labels(cache_type=cache_type).inc()


# --- Business Instrumentation ---
def record_dataset_registered():
    datasets_registered_total.inc()


# --- System Background Task ---
async def collect_system_metrics(interval_seconds: int = 10):
    """Background task to poll system metrics periodically."""
    psutil.cpu_percent(interval=None)  # Initialize CPU percentage
    while True:
        try:
            process = psutil.Process()
            cpu = process.cpu_percent(interval=None)
            memory = process.memory_info().rss
            process_cpu_percent.set(cpu)
            process_memory_bytes.set(memory)
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)
