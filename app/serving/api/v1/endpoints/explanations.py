from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.storage.database import get_db
from app.storage.models import ExplanationMetadata, GlobalExplanationSummary
from app.explainability.schemas import (
    ExplanationResponse,
    CacheStatisticsResponse,
    GlobalExplanationResponse,
    ExplanationStatisticsResponse,
    GenerateExplanationRequest
)
from app.explainability.cache import get_explanation_cache
from app.explainability.manager import ExplanationManager
from app.security.dependencies import RequireRole

router = APIRouter(prefix="/explanations", tags=["explainability"])


@router.get("/{prediction_id}", response_model=ExplanationResponse)
async def get_explanation(
    prediction_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(RequireRole(["ADMIN", "ML_ENGINEER", "DATA_SCIENTIST", "VIEWER"]))
):
    """Retrieve an explanation for a specific prediction ID."""
    result = await db.execute(
        select(ExplanationMetadata).filter(ExplanationMetadata.prediction_id == prediction_id)
    )
    meta = result.scalars().first()

    if not meta:
        raise HTTPException(status_code=404, detail="Explanation not found or still generating.")

    user_id = user["id"] if isinstance(user, dict) else user.id

    user_role = ""
    if isinstance(user, dict):
        user_role = user.get("role", "")
    else:
        from app.storage.models import Role
        role_result = await db.execute(select(Role.name).filter(Role.id == user.role_id))
        user_role = role_result.scalar_one_or_none()

    if user_role == "VIEWER" and meta.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this explanation.")

    return ExplanationResponse(
        prediction_id=meta.prediction_id,
        model_id=meta.model_id,
        generation_time_ms=meta.generation_time_ms or 0.0,
        execution_time=meta.execution_time,
        cache_status=meta.cache_status,
        top_features=meta.top_features or [],
        visualization_data=meta.visualization_data or {},
        explanation_version=meta.explanation_version,
        model_version=meta.model_version,
        feature_version=meta.feature_version,
        dataset_version=meta.dataset_version,
        shap_library_version=meta.shap_library_version
    )


@router.get("/history/{model_id}", response_model=List[ExplanationResponse])
async def get_explanation_history(
    model_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(RequireRole(["ADMIN", "ML_ENGINEER", "DATA_SCIENTIST"]))
):
    """Retrieve historical explanations for a specific model."""
    result = await db.execute(
        select(ExplanationMetadata)
        .filter(ExplanationMetadata.model_id == model_id)
        .order_by(ExplanationMetadata.created_at.desc())
        .limit(limit)
    )
    history = result.scalars().all()

    return [
        ExplanationResponse(
            prediction_id=meta.prediction_id,
            model_id=meta.model_id,
            generation_time_ms=meta.generation_time_ms or 0.0,
            execution_time=meta.execution_time,
            cache_status=meta.cache_status,
            top_features=meta.top_features or [],
            visualization_data=meta.visualization_data or {},
            explanation_version=meta.explanation_version,
            model_version=meta.model_version,
            feature_version=meta.feature_version,
            dataset_version=meta.dataset_version,
            shap_library_version=meta.shap_library_version
        ) for meta in history
    ]


@router.get("/global/{model_id}", response_model=GlobalExplanationResponse)
async def get_global_explanation(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(RequireRole(["ADMIN", "ML_ENGINEER", "DATA_SCIENTIST", "VIEWER"]))
):
    """Retrieve global explainability metrics for a model."""
    result = await db.execute(
        select(GlobalExplanationSummary)
        .filter(GlobalExplanationSummary.model_id == model_id)
        .order_by(GlobalExplanationSummary.created_at.desc())
    )
    summary = result.scalars().first()

    if not summary:
        raise HTTPException(status_code=404, detail="Global explanation not available.")

    return GlobalExplanationResponse(
        model_id=summary.model_id,
        dataset_id=summary.dataset_id,
        model_version=summary.model_version,
        global_feature_importance=summary.global_feature_importance or [],
        top_n_features=summary.top_n_features or [],
        created_at=summary.created_at
    )


@router.get("/statistics", response_model=ExplanationStatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(RequireRole(["ADMIN", "ML_ENGINEER"]))
):
    """Retrieve global explanation statistics across the platform."""
    total = await db.execute(select(func.count()).select_from(ExplanationMetadata))
    hits = await db.execute(select(func.count()).select_from(ExplanationMetadata).filter(ExplanationMetadata.cache_status == "HIT"))
    avg_latency = await db.execute(select(func.avg(ExplanationMetadata.generation_time_ms)))

    total_val = total.scalar() or 0
    hits_val = hits.scalar() or 0
    misses_val = total_val - hits_val
    hit_ratio = (hits_val / total_val) if total_val > 0 else 0.0
    latency_val = avg_latency.scalar() or 0.0

    return ExplanationStatisticsResponse(
        total_explanations_generated=total_val,
        average_generation_time_ms=float(latency_val),
        cache_hit_rate=hit_ratio,
        total_cache_hits=hits_val,
        total_cache_misses=misses_val
    )


@router.post("/generate")
async def generate_explanation(
    payload: GenerateExplanationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(RequireRole(["ADMIN", "ML_ENGINEER"]))
):
    """Off-cycle background generation for an existing prediction."""
    # To generate, we need the original features from PredictionCache
    from app.serving.dependencies import get_prediction_engine

    engine = get_prediction_engine()
    model_id, version = engine.routing_registry.get(payload.model_alias, (None, None))

    if not model_id:
        raise HTTPException(status_code=400, detail="Model alias not found.")

    predictor = engine.predictors.get(model_id)
    if not predictor:
        raise HTTPException(status_code=400, detail="Predictor not loaded in memory.")

    m_ver = f"v{predictor.metadata.version}" if predictor.metadata else "v1"
    f_ver = str(predictor.metadata.version) if (predictor.metadata and predictor.metadata.dataset_id) else "1"

    mgr = ExplanationManager()
    user_id = user["id"] if isinstance(user, dict) else user.id

    background_tasks.add_task(
        mgr.generate_background,
        prediction_id=payload.prediction_id,
        model_id=model_id,
        m_ver=m_ver,
        f_ver=f_ver,
        features=payload.features,
        predictor=predictor,
        user_id=user_id
    )

    return {"status": "generating", "prediction_id": payload.prediction_id, "poll_url": f"/api/v1/explanations/{payload.prediction_id}"}


@router.get("/cache", response_model=CacheStatisticsResponse)
async def get_cache_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(RequireRole(["ADMIN", "ML_ENGINEER"]))
):
    """Retrieve explanation cache statistics."""
    cache = get_explanation_cache()
    if not cache.redis.client:
        raise HTTPException(status_code=503, detail="Redis is not connected.")

    # Example logic using DB to aggregate stats since Redis doesn't store miss counters easily
    total = await db.execute(select(func.count()).select_from(ExplanationMetadata))
    hits = await db.execute(select(func.count()).select_from(ExplanationMetadata).filter(ExplanationMetadata.cache_status == "HIT"))

    total_val = total.scalar() or 0
    hits_val = hits.scalar() or 0
    misses_val = total_val - hits_val
    hit_ratio = (hits_val / total_val) if total_val > 0 else 0.0

    return CacheStatisticsResponse(
        total_requests=total_val,
        cache_hits=hits_val,
        cache_misses=misses_val,
        hit_ratio=hit_ratio,
        average_latency_ms=0.0,  # Could aggregate from DB
        total_memory_usage_mb=0.0
    )


@router.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache(
    user: dict = Depends(RequireRole(["ADMIN", "ML_ENGINEER"]))
):
    """Invalidate all cached explanations."""
    cache = get_explanation_cache()
    if cache.redis.client:
        # Warning: Keys blocks. In production use SCAN, but acceptable here.
        keys = await cache.redis.client.keys(f"{cache.prefix}:*")
        if keys:
            await cache.redis.client.delete(*keys)
    return None
