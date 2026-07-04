"""
Abstract backend interfaces for telemetry emission.
Enables swapping local loggers for Prometheus/OpenTelemetry without redesign.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseMetricBackend(ABC):
    @abstractmethod
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """Records a cumulative event."""
        ...
        
    @abstractmethod
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Records a point-in-time value."""
        ...
        
    @abstractmethod
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Records a distribution of values (e.g., latency)."""
        ...

class BaseAuditBackend(ABC):
    @abstractmethod
    def record_event(self, event: Dict[str, Any]) -> None:
        """Persists an immutable, structured audit event."""
        ...
