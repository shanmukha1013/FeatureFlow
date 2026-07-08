"""
Exposes read-only access to platform registries.
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.storage.database import get_db
from app.storage.models import Dataset, Feature, Model, Experiment, ChampionModel, AuditLog
from app.serving.api.v1.management.schemas.pagination import PaginatedResponse

router = APIRouter()

def paginate(items: List[Any], page: int, size: int) -> PaginatedResponse[Any]:
    total = len(items)
    start = (page - 1) * size
    end = start + size
    sliced = items[start:end]
    has_next = end < total
    return PaginatedResponse(items=sliced, total=total, page=page, size=size, has_next=has_next)

@router.get("/datasets", response_model=PaginatedResponse[Any])
async def get_datasets(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    result = await session.execute(select(Dataset).order_by(desc(Dataset.created_at)))
    datasets = result.scalars().all()
    items = []
    for d in datasets:
        items.append({
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "status": d.status,
            "version": d.version,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "inferred_dtypes": d.inferred_dtypes
        })
    return paginate(items, page, size)

@router.get("/features", response_model=PaginatedResponse[Any])
async def get_features(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100),
    search: str = None,
    dataset: str = None,
    sort_by: str = "created_at",
    sort_desc: bool = True,
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    
    query = select(Feature).options(selectinload(Feature.dataset))
    if search:
        query = query.filter(Feature.name.ilike(f"%{search}%"))
    
    # Simple sort assuming valid column
    if sort_desc:
        query = query.order_by(desc(getattr(Feature, sort_by, Feature.created_at)))
    else:
        query = query.order_by(getattr(Feature, sort_by, Feature.created_at))

    result = await session.execute(query)
    features = result.scalars().all()
    
    items = []
    for f in features:
        # Resolve dataset name manually if dataset filter is active
        # The schema uses backref 'dataset'
        ds_name = f.dataset.name if f.dataset else ""
        if dataset and dataset.lower() != ds_name.lower():
            continue
            
        items.append({
            "id": f.id,
            "name": f.name,
            "dtype": f.dtype,
            "transformation": f.transformation,
            "status": f.status,
            "version": f.version,
            "source_dataset": ds_name,
            "created_at": f.created_at.isoformat() if f.created_at else None
        })
        
    return paginate(items, page, size)

@router.get("/models", response_model=PaginatedResponse[Any])
async def get_models(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100), 
    status: str = None,
    search: str = None,
    dataset: str = None,
    sort_by: str = "created_at",
    sort_desc: bool = True,
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    query = select(Model).options(selectinload(Model.dataset))
    if status:
        query = query.filter(Model.status == status)
    if search:
        query = query.filter(Model.name.ilike(f"%{search}%"))
        
    if sort_desc:
        query = query.order_by(desc(getattr(Model, sort_by, Model.created_at)))
    else:
        query = query.order_by(getattr(Model, sort_by, Model.created_at))

    result = await session.execute(query)
    models = result.scalars().all()
    
    items = []
    for m in models:
        ds_name = m.dataset.name if m.dataset else ""
        if dataset and dataset.lower() != ds_name.lower():
            continue
            
        items.append({
            "id": m.id,
            "name": m.name,
            "version": m.version,
            "status": m.status,
            "metrics": m.metrics,
            "hyperparameters": m.hyperparameters,
            "dataset_version": ds_name,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })
        
    return paginate(items, page, size)

@router.get("/inference")
async def get_inference_stats():
    from app.serving.dependencies import _prediction_engine
    
    loaded_models = []
    for model_id, predictor in _prediction_engine.predictors.items():
        loaded_models.append({
            "model_id": model_id,
            "version": predictor.version,
            "algorithm": predictor.metadata.algorithm if predictor.metadata else "Unknown",
            "dataset": predictor.metadata.dataset_version if predictor.metadata else "Unknown"
        })
        
    return {
        "loaded_models": loaded_models,
        "prediction_count": _prediction_engine.stats["prediction_count"],
        "average_latency_ms": _prediction_engine.stats["total_latency_ms"] / max(1, _prediction_engine.stats["prediction_count"]),
        "cache_size": len(_prediction_engine.predictors),
        "last_prediction": _prediction_engine.stats["last_prediction_time"]
    }

@router.get("/experiments", response_model=PaginatedResponse[Any])
async def get_experiments(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100),
    dataset: str = None,
    algorithm: str = None,
    status: str = None,
    tag: str = None,
    sort_by: str = "start_time",
    sort_desc: bool = True,
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    query = select(Experiment).options(selectinload(Experiment.dataset))
    if algorithm:
        query = query.filter(Experiment.algorithm == algorithm)
    if status:
        query = query.filter(Experiment.status == status)
        
    if sort_desc:
        query = query.order_by(desc(getattr(Experiment, sort_by, Experiment.created_at)))
    else:
        query = query.order_by(getattr(Experiment, sort_by, Experiment.created_at))

    result = await session.execute(query)
    exps = result.scalars().all()
    
    items = []
    for e in exps:
        ds_name = e.dataset.name if e.dataset else ""
        if dataset and dataset.lower() != ds_name.lower():
            continue
        
        items.append({
            "id": e.id,
            "name": e.name,
            "algorithm": e.algorithm,
            "status": e.status,
            "hyperparameters": e.hyperparameters,
            "metrics": e.metrics,
            "dataset": ds_name,
            "start_time": e.created_at.isoformat() if e.created_at else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
        })
        
    return paginate(items, page, size)

@router.get("/experiments/compare")
async def compare_experiments(ids: str = Query(..., description="Comma separated experiment IDs"), session: AsyncSession = Depends(get_db)):
    from app.monitoring.audit import AuditLogger, AuditEvent
    exp_ids = [e.strip() for e in ids.split(",") if e.strip()]
    
    result = await session.execute(select(Experiment).filter(Experiment.id.in_(exp_ids)))
    exps = result.scalars().all()
    
    res = {}
    for e in exps:
        res[e.id] = {
            "name": e.name,
            "algorithm": e.algorithm,
            "metrics": e.metrics,
            "hyperparameters": e.hyperparameters
        }
        
    await AuditLogger.record(session, AuditEvent(event_name="EXPERIMENT_COMPARED", component="ManagementAPI", severity="INFO", payload={"experiment_ids": exp_ids}))
    return res

@router.get("/experiments/{id}")
async def get_experiment(id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Experiment).filter(Experiment.id == id))
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    return {
        "id": exp.id,
        "name": exp.name,
        "algorithm": exp.algorithm,
        "status": exp.status,
        "hyperparameters": exp.hyperparameters,
        "metrics": exp.metrics,
        "dataset": exp.dataset.name if exp.dataset else "",
        "start_time": exp.created_at.isoformat() if exp.created_at else None,
        "end_time": exp.end_time.isoformat() if exp.end_time else None,
    }

@router.get("/models/{id}/importance")
async def get_model_importance(id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Model).filter(Model.id == id))
    model = result.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Since feature importance is not stored directly on Model right now (it's in an artifact or metadata)
    # We will return empty for now, or fetch from Model if we add it. 
    # For now, it returns empty dict as placeholder.
    return {"model_id": id, "feature_importance": {}}

@router.get("/models/{id}/explanation")
async def get_model_explanation(id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Model).filter(Model.id == id))
    model = result.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"model_id": id, "shap_summary": {}}

@router.get("/drift")
async def get_drift_status(model_id: str = None, session: AsyncSession = Depends(get_db)):
    """Generates a live drift report for a specific model."""
    from app.monitoring.drift.engine import global_drift_engine
    
    if not model_id:
        # Default to the first champion model
        result = await session.execute(select(ChampionModel))
        champ = result.scalars().first()
        if not champ:
            raise HTTPException(status_code=400, detail="No model_id provided and no champion found.")
        model_id = champ.model_id
            
    try:
        # In a real implementation we would fetch the baseline profile from the artifact/DB
        baseline_profile = {} 
        report = global_drift_engine.generate_report(model_id, baseline_profile)
        
        from dataclasses import asdict
        report_dict = asdict(report)
        report_dict["timestamp"] = report.timestamp.isoformat()
        report_dict["severity"] = report.severity.value
        return report_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate drift report: {e}")

@router.get("/drift/history")
async def get_drift_history(session: AsyncSession = Depends(get_db)):
    """Fetches historical drift alerts from the audit logger."""
    result = await session.execute(select(AuditLog).filter(AuditLog.event_name.in_(["DRIFT_DETECTED", "FEATURE_DRIFT", "MODEL_DRIFT"])).order_by(desc(AuditLog.created_at)).limit(100))
    logs = result.scalars().all()
    
    history = []
    for log in logs:
        history.append({
            "event_name": log.event_name,
            "component": log.component,
            "severity": log.severity,
            "payload": log.payload,
            "created_at": log.created_at.isoformat()
        })
    return {"history": history}

@router.get("/drift/{feature}")
async def get_feature_drift(feature: str, model_id: str = None, session: AsyncSession = Depends(get_db)):
    """Gets drift specifically for one feature."""
    report = await get_drift_status(model_id, session)
    feature_drift = [f for f in report.get("drifted_features", []) if f["feature"] == feature]
    return {"feature": feature, "drift": feature_drift[0] if feature_drift else None}
