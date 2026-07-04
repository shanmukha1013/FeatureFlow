"""
Local implementations of monitoring backends.
Caches metrics in memory and writes audit events to structured stdout.
"""
from typing import Dict, Any
from app.monitoring.backends.base import BaseMetricBackend, BaseAuditBackend
from app.utils.logger import get_logger

logger = get_logger(__name__)

class LocalMetricBackend(BaseMetricBackend):
    def __init__(self) -> None:
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = {}

    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        key = f"{name}_{tags}" if tags else name
        self.counters[key] = self.counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        key = f"{name}_{tags}" if tags else name
        self.gauges[key] = value

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        key = f"{name}_{tags}" if tags else name
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)

class LocalAuditBackend(BaseAuditBackend):
    def __init__(self) -> None:
        self.events = []

    def record_event(self, event: Dict[str, Any]) -> None:
        logger.info(f"AUDIT EVENT: {event}")
        self.events.insert(0, event)
