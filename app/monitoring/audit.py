"""
Immutable audit event recording.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from app.monitoring.backends.base import BaseAuditBackend
from app.monitoring.backends.local import LocalAuditBackend
from app.monitoring.config import monitoring_config

@dataclass(frozen=True)
class AuditEvent:
    """
    Structured, immutable definition of a discrete platform event.
    """
    event_name: str
    component: str
    severity: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "event_name": self.event_name,
            "component": self.component,
            "severity": self.severity,
            "payload": self.payload
        }

_backend: BaseAuditBackend = LocalAuditBackend()

class AuditLogger:
    """
    Centralized router for audit events.
    """
    @staticmethod
    def record(event: AuditEvent) -> None:
        if monitoring_config.enable_audit:
            _backend.record_event(event.to_dict())
