"""
Local (stdout/log) monitoring backends.

Provides lightweight implementations for development/testing that write
metrics and audit events to the application logger instead of an external service.
These are NOT used in production — PostgreSQL is the audit backend.
"""
import json
from typing import Any, Dict

from app.monitoring.backends.base import BaseMetricBackend, BaseAuditBackend
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LocalMetricBackend(BaseMetricBackend):
    """
    Logs metrics to the application logger.
    No external dependency. Suitable for local development.
    """

    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        tag_str = json.dumps(tags) if tags else "{}"
        logger.debug(f"[METRIC] {name}={value} tags={tag_str}")

    def flush(self) -> None:
        pass  # No-op for local backend


class LocalAuditBackend(BaseAuditBackend):
    """
    Logs audit events to the application logger.
    In production, audit events go directly to PostgreSQL via AuditService.
    """

    def record_event(self, event_data: Dict[str, Any]) -> None:
        logger.info(f"[AUDIT] {json.dumps(event_data, default=str)}")
