"""
Abstract base contracts for monitoring backends.

Defines interfaces for metric collection and audit logging backends
so that concrete implementations can be swapped freely.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseMetricBackend(ABC):
    """Abstract interface for metric storage backends."""

    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a numeric metric with optional tags."""
        ...

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered metrics to the backend."""
        ...


class BaseAuditBackend(ABC):
    """Abstract interface for audit event storage backends."""

    @abstractmethod
    def record_event(self, event_data: Dict[str, Any]) -> None:
        """Persist a structured audit event."""
        ...
