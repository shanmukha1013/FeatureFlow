from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from app.storage.database import get_db
from app.monitoring.schemas import MonitoringRunRequest, MonitoringReportResponse
from app.monitoring.service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/run", response_model=MonitoringReportResponse)
async def run_drift_analysis(
    request: MonitoringRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers an asynchronous-style (but currently blocking for fast track) Evidently AI drift analysis
    comparing a reference dataset against a current dataset.
    """
    service = MonitoringService(db)
    try:
        report = await service.run_drift_analysis(
            reference_dataset_id=request.reference_dataset_id,
            current_dataset_id=request.current_dataset_id
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/latest", response_class=HTMLResponse)
async def get_latest_report(
    dataset_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the latest HTML drift report for a given current dataset ID.
    Attempts to serve from Redis cache first for ultra-low latency, falling back to disk.
    """
    service = MonitoringService(db)
    html_content = await service.get_latest_report_html(dataset_id)
    if not html_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report found for this dataset.")
    return html_content


@router.get("/history", response_model=List[MonitoringReportResponse])
async def get_report_history(
    dataset_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the metadata history of all drift reports generated for a given current dataset ID.
    """
    service = MonitoringService(db)
    reports = await service.get_history(dataset_id=dataset_id, limit=limit)
    return reports
