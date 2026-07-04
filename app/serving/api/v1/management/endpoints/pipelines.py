"""
Exposes pipeline execution reports.
"""
from fastapi import APIRouter, Query
from typing import Any
from app.serving.api.v1.management.schemas.pagination import PaginatedResponse

router = APIRouter()

@router.get("/pipelines", response_model=PaginatedResponse[Any])
def get_pipelines(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100)):
    items = []
    try:
        from app.pipelines.pipeline import _pipeline_history
        # Convert reports to dicts or strings
        items = [r.__dict__ if hasattr(r, '__dict__') else str(r) for r in _pipeline_history]
    except Exception:
        pass
        
    total = len(items)
    start = (page - 1) * size
    end = start + size
    sliced = items[start:end]
    has_next = end < total
    return PaginatedResponse(items=sliced, total=total, page=page, size=size, has_next=has_next)
