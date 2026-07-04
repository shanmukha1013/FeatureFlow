"""
Centralized configuration for the Monitoring & Observability Layer.
Isolates thresholds and sampling rates from business logic.
"""
class MonitoringConfig:
    alert_latency_ms: float = 200.0
    alert_error_rate_threshold: float = 0.05
    backend: str = "local"
    enable_metrics: bool = True
    enable_audit: bool = True
    sampling_rate: float = 1.0

monitoring_config = MonitoringConfig()
