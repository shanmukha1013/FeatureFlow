"""
Public boundary for the Monitoring & Observability Layer.
"""
from .audit import AuditEvent, AuditLogger
from .config import monitoring_config
from .health import HealthMonitor, HealthStatus
from .logger import correlation_id_var, setup_structured_logging
from .middleware import monitoring_middleware

__all__ = [
    "monitoring_config",
    "AuditLogger",
    "AuditEvent",
    "setup_structured_logging",
    "correlation_id_var",
    "HealthStatus",
    "HealthMonitor",
    "monitoring_middleware"
]
