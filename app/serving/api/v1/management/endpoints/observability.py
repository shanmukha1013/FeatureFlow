"""
Exposes telemetry, health, and audit logs.
"""
from fastapi import APIRouter, Query, Depends
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, text
from app.serving.api.v1.management.schemas.pagination import PaginatedResponse
from app.monitoring.health import HealthMonitor
from app.storage.database import get_db

router = APIRouter()

@router.get("/audit", response_model=PaginatedResponse[Any])
async def get_audit(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    from app.storage.models import AuditLog
    
    start = (page - 1) * size
    query = select(AuditLog).order_by(desc(AuditLog.created_at)).offset(start).limit(size + 1)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    has_next = len(logs) > size
    items = logs[:size]
    
    out_items = [{
        "id": row.id,
        "timestamp": row.created_at.isoformat() if row.created_at else None,
        "event_name": row.event_name,
        "component": row.component,
        "severity": row.severity,
        "payload": row.payload
    } for row in items]
    
    return PaginatedResponse(items=out_items, total=0, page=page, size=size, has_next=has_next)

@router.get("/health")
def get_health():
    """Returns deep dependency probe results."""
    return HealthMonitor.check_health()

@router.get("/health/database")
async def get_database_health(session: AsyncSession = Depends(get_db)):
    """Verifies database connectivity, connection pool stats, and runs a read/write test."""
    import time
    try:
        # Read Test
        start_time = time.perf_counter()
        await session.execute(text("SELECT 1"))
        read_latency_ms = (time.perf_counter() - start_time) * 1000

        # Write Test inside nested transaction that we rollback
        write_latency_ms = 0.0
        async with session.begin_nested():
            w_start_time = time.perf_counter()
            from app.storage.models import SystemMetric
            test_metric = SystemMetric(metric_name="health_check_ping", metric_value=1.0)
            session.add(test_metric)
            await session.flush()
            write_latency_ms = (time.perf_counter() - w_start_time) * 1000
            await session.rollback() # Never commit the test write

        # Connection Pool Stats
        pool = session.bind.pool
        pool_stats = {
            "size": pool.size(),
            "checkedin": pool.checkedin(),
            "checkedout": pool.checkedout(),
            "overflow": pool.overflow()
        }

        return {
            "status": "healthy",
            "database": "postgresql",
            "read_latency_ms": round(read_latency_ms, 2),
            "write_latency_ms": round(write_latency_ms, 2),
            "pool": pool_stats,
            "message": "Read/Write tests passed. Transaction rollback successful."
        }
    except Exception as e:
        return {"status": "unhealthy", "database": "postgresql", "error": str(e)}

@router.get("/metrics")
async def get_metrics(session: AsyncSession = Depends(get_db)):
    """Generates metrics dynamically from SQL queries."""
    from app.storage.models import AuditLog
    
    # Simple metric generation
    # Number of predictions
    pred_query = select(AuditLog).filter(AuditLog.event_name == 'PREDICTION_FINISHED')
    res = await session.execute(pred_query)
    pred_count = len(res.scalars().all())
    
    # We can add more metrics dynamically without a caching daemon
    return {
        "counters": {
            "prediction.requests": pred_count
        },
        "gauges": {},
        "histograms": {}
    }
