from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.storage.database import get_db
from app.security.dependencies import get_current_user
from app.data_quality.models import DataContractModel, ValidationRun, ExpectationSuiteModel
from app.data_quality.schemas import DataContractResponse, ValidationRunResponse
from app.data_quality.manager import DataQualityCacheManager
from sqlalchemy.future import select
from sqlalchemy import desc

router = APIRouter()


@router.get("/contracts", response_model=List[DataContractResponse])
async def list_data_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    dataset_name: str = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    stmt = select(DataContractModel).order_by(desc(DataContractModel.created_at))
    if dataset_name:
        stmt = stmt.filter_by(dataset_name=dataset_name)

    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/health/{dataset_name}")
async def get_dataset_health(
    dataset_name: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 1. Try cache
    cache = DataQualityCacheManager()
    score = await cache.get_health_score(dataset_name)
    if score is not None:
        return {"dataset_name": dataset_name, "health_score": score, "cached": True}

    # 2. Fallback to DB
    stmt = select(ValidationRun).join(ExpectationSuiteModel).join(DataContractModel)\
        .filter(DataContractModel.dataset_name == dataset_name)\
        .order_by(desc(ValidationRun.created_at)).limit(1)

    result = await db.execute(stmt)
    latest_run = result.scalar_one_or_none()

    if latest_run:
        await cache.cache_health_score(dataset_name, latest_run.quality_score)
        return {"dataset_name": dataset_name, "health_score": latest_run.quality_score, "cached": False}

    raise HTTPException(status_code=404, detail="No health score found for dataset")


@router.get("/runs/{dataset_version_id}", response_model=List[ValidationRunResponse])
async def list_validation_runs(
    dataset_version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    stmt = select(ValidationRun).filter_by(dataset_version_id=dataset_version_id).order_by(desc(ValidationRun.created_at))
    result = await db.execute(stmt)
    runs = result.scalars().all()

    # Normally we would join results here or use selectinload, but for simplicity we rely on lazy loading or omit results list in overview.
    # To prevent n+1 queries, let's just return the top level runs.
    return runs
