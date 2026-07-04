"""
Exposes telemetry, health, and audit logs.
"""
from fastapi import APIRouter, Query
from typing import Any
from app.serving.api.v1.management.schemas.pagination import PaginatedResponse
from app.monitoring.health import HealthMonitor

router = APIRouter()

@router.get("/audit", response_model=PaginatedResponse[Any])
def get_audit(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100)):
    items = []
    try:
        from app.monitoring.audit import _backend
        if hasattr(_backend, "events"):
            items = _backend.events
    except Exception:
        pass
        
    total = len(items)
    start = (page - 1) * size
    end = start + size
    sliced = items[start:end]
    has_next = end < total
    return PaginatedResponse(items=sliced, total=total, page=page, size=size, has_next=has_next)

@router.get("/health")
def get_health():
    """Returns deep dependency probe results."""
    return HealthMonitor.check_health()

@router.get("/metrics")
def get_metrics():
    """Scrapes raw metrics directly from the Local backend."""
    try:
        from app.monitoring.metrics import _backend
        return {
            "counters": getattr(_backend, "counters", {}),
            "gauges": getattr(_backend, "gauges", {}),
            "histograms": getattr(_backend, "histograms", {})
        }
    except Exception:
        return {"counters": {}, "gauges": {}, "histograms": {}}
