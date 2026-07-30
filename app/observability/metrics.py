from prometheus_client import Counter, Gauge, Histogram

# HTTP Metrics
http_requests_total = Counter(
    "featureflow_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "featureflow_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

http_requests_active = Gauge(
    "featureflow_http_requests_active",
    "Number of currently active HTTP requests"
)

# Prediction Metrics
prediction_requests_total = Counter(
    "featureflow_prediction_requests_total",
    "Total prediction requests",
    ["model_name"]
)

prediction_latency_seconds = Histogram(
    "featureflow_prediction_latency_seconds",
    "Latency of prediction requests",
    ["model_name"]
)

prediction_failures_total = Counter(
    "featureflow_prediction_failures_total",
    "Total prediction failures",
    ["model_name", "reason"]
)

# Training Metrics
training_runs_total = Counter(
    "featureflow_training_runs_total",
    "Total training runs",
    ["algorithm"]
)

training_duration_seconds = Histogram(
    "featureflow_training_duration_seconds",
    "Duration of training runs",
    ["algorithm"]
)

training_failures_total = Counter(
    "featureflow_training_failures_total",
    "Total training failures",
    ["algorithm"]
)

# MLflow Metrics
mlflow_experiments_created_total = Counter(
    "featureflow_mlflow_experiments_created_total",
    "Total MLflow experiments created"
)

mlflow_models_registered_total = Counter(
    "featureflow_mlflow_models_registered_total",
    "Total models registered in MLflow"
)

mlflow_models_promoted_total = Counter(
    "featureflow_mlflow_models_promoted_total",
    "Total models promoted in MLflow",
    ["alias"]
)

# Evidently Metrics
drift_checks_total = Counter(
    "featureflow_drift_checks_total",
    "Total drift checks executed"
)

drift_detected_total = Counter(
    "featureflow_drift_detected_total",
    "Total times drift was detected"
)

# Infrastructure / Caching Metrics
cache_hits_total = Counter(
    "featureflow_cache_hits_total",
    "Total cache hits",
    ["cache_type"]
)

cache_misses_total = Counter(
    "featureflow_cache_misses_total",
    "Total cache misses",
    ["cache_type"]
)

# Business Metrics
datasets_registered_total = Counter(
    "featureflow_datasets_registered_total",
    "Total datasets registered"
)

# System Metrics
process_cpu_percent = Gauge(
    "featureflow_process_cpu_percent",
    "Process CPU utilization percentage"
)

process_memory_bytes = Gauge(
    "featureflow_process_memory_bytes",
    "Process memory usage in bytes"
)
