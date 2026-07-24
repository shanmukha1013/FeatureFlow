import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

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


class AuditLogger:
    """
    Centralized router for audit events.
    Now requires a database session to persist to PostgreSQL.
    """
    @staticmethod
    async def record(session: AsyncSession, event: AuditEvent) -> None:
        if monitoring_config.enable_audit:
            from app.services.audit import AuditService
            audit_service = AuditService(session)
            await audit_service.record(event)
