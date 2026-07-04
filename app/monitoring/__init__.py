"""
Public boundary for the Monitoring & Observability Layer.
"""
from .config import monitoring_config
from .metrics import MetricsRegistry
from .audit import AuditLogger, AuditEvent
from .logger import setup_structured_logging, correlation_id_var
from .health import HealthStatus, HealthMonitor
from .decorators import track_latency, count_invocations, audit_event
from .middleware import monitoring_middleware

__all__ = [
    "monitoring_config",
    "MetricsRegistry",
    "AuditLogger",
    "AuditEvent",
    "setup_structured_logging",
    "correlation_id_var",
    "HealthStatus",
    "HealthMonitor",
    "track_latency",
    "count_invocations",
    "audit_event",
    "monitoring_middleware"
]
