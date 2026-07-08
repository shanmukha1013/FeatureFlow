"""
Exposes pipeline execution reports.
"""
from fastapi import APIRouter, Query, Depends
from typing import Any
from app.serving.api.v1.management.schemas.pagination import PaginatedResponse
from app.storage.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

router = APIRouter()

@router.get("/pipelines", response_model=PaginatedResponse[Any])
async def get_pipelines(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    from app.storage.models import AuditLog
    
    start = (page - 1) * size
    
    # Query logs indicating pipeline progression
    query = select(AuditLog).filter(
        AuditLog.event_name.in_([
            'DATASET_DISCOVERED', 
            'DATASET_VALIDATED', 
            'PROFILING_COMPLETED',
            'FEATURE_GENERATED',
            'MODEL_TRAINED',
            'PIPELINE_FAILED'
        ])
    ).order_by(desc(AuditLog.created_at)).offset(start).limit(size + 1)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    has_next = len(logs) > size
    items = logs[:size]
    
    # Convert to dict
    out_items = []
    for row in items:
        out_items.append({
            "id": row.id,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            "event_name": row.event_name,
            "component": row.component,
            "severity": row.severity,
            "payload": row.payload
        })
        
    return PaginatedResponse(
        items=out_items, 
        total=0, # total count omitted for performance, could do a COUNT query
        page=page, 
        size=size, 
        has_next=has_next
    )
