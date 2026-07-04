"""
Generic metric abstractions decoupled from concrete time-series databases.
"""
from typing import Dict
from app.monitoring.backends.base import BaseMetricBackend
from app.monitoring.backends.local import LocalMetricBackend
from app.monitoring.config import monitoring_config

# Singleton backend resolution. Hardcoded to LocalMetricBackend for now, 
# but easily extensible to PrometheusMetricBackend later.
_backend: BaseMetricBackend = LocalMetricBackend()

class MetricsRegistry:
    """
    Centralized, thread-safe entry point for recording platform metrics.
    """
    @staticmethod
    def increment(name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        if monitoring_config.enable_metrics:
            _backend.increment_counter(name, value, tags)
            
    @staticmethod
    def gauge(name: str, value: float, tags: Dict[str, str] = None) -> None:
        if monitoring_config.enable_metrics:
            _backend.set_gauge(name, value, tags)
            
    @staticmethod
    def histogram(name: str, value: float, tags: Dict[str, str] = None) -> None:
        if monitoring_config.enable_metrics:
            _backend.record_histogram(name, value, tags)
