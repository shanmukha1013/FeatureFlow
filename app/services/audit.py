from sqlalchemy.ext.asyncio import AsyncSession
from app.monitoring.audit import AuditEvent
from app.storage.repositories.core import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession):
        self.repository = AuditLogRepository(session)

    async def record(self, event: AuditEvent):
        await self.repository.create({
            "event_name": event.event_name,
            "component": event.component,
            "severity": event.severity,
            "payload": event.payload,
            "status": "RECORDED"
        })
