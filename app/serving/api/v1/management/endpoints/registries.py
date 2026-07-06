"""
Exposes read-only access to platform registries.
"""
from fastapi import APIRouter, Query
from typing import Any, List
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
def get_datasets(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100)):
    items = []
    try:
        from app.data.dataset_registry import global_dataset_registry
        datasets = global_dataset_registry.list_datasets()
        items = [d.__dict__ for d in datasets]
    except Exception:
        pass
    return paginate(items, page, size)

@router.get("/features", response_model=PaginatedResponse[Any])
def get_features(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100),
    search: str = None,
    dataset: str = None,
    sort_by: str = "created_at",
    sort_desc: bool = True
):
    items = []
    try:
        from app.features.registry import global_feature_registry
        for name in global_feature_registry.list_features():
            feat = global_feature_registry.get(name)
            if hasattr(feat, "metadata"):
                meta_dict = feat.metadata.__dict__
                
                # Filtering
                if search and search.lower() not in meta_dict.get("name", "").lower():
                    continue
                if dataset and dataset.lower() != meta_dict.get("source_dataset", "").lower():
                    continue
                    
                items.append(meta_dict)
                
        # Sorting
        if sort_by in items[0] if items else False:
            items.sort(key=lambda x: x.get(sort_by, ""), reverse=sort_desc)
            
    except Exception:
        pass
    return paginate(items, page, size)

@router.get("/models", response_model=PaginatedResponse[Any])
def get_models(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100), 
    status: str = None,
    search: str = None,
    dataset: str = None,
    sort_by: str = "training_timestamp",
    sort_desc: bool = True
):
    items = []
    try:
        from app.serving.dependencies import _training_registry
        model_ids = _training_registry.list_models()
        for mid in model_ids:
            meta = _training_registry.get(mid)
            meta_dict = meta.to_dict()
            
            if status and getattr(meta, "lifecycle_state", None) != status:
                continue
            if search and search.lower() not in meta_dict.get("algorithm", "").lower() and search.lower() not in mid.lower():
                continue
            if dataset and dataset.lower() != meta_dict.get("dataset_version", "").lower():
                continue
                
            items.append(meta_dict)
            
        if sort_by in items[0] if items else False:
            items.sort(key=lambda x: x.get(sort_by, ""), reverse=sort_desc)
            
    except Exception:
        pass
    return paginate(items, page, size)

@router.get("/inference")
def get_inference_stats():
    from app.serving.dependencies import _prediction_engine
    
    loaded_models = []
    for model_id, predictor in _prediction_engine.predictors.items():
        loaded_models.append({
            "model_id": model_id,
            "version": predictor.version,
            "algorithm": predictor.metadata.algorithm,
            "dataset": predictor.metadata.dataset_version
        })
        
    return {
        "loaded_models": loaded_models,
        "prediction_count": _prediction_engine.stats["prediction_count"],
        "average_latency_ms": _prediction_engine.stats["total_latency_ms"] / max(1, _prediction_engine.stats["prediction_count"]),
        "cache_size": len(_prediction_engine.predictors),
        "last_prediction": _prediction_engine.stats["last_prediction_time"]
    }

@router.get("/experiments", response_model=PaginatedResponse[Any])
def get_experiments(
    page: int = Query(1, ge=1), 
    size: int = Query(50, ge=1, le=100),
    dataset: str = None,
    algorithm: str = None,
    status: str = None,
    tag: str = None,
    sort_by: str = "start_time",
    sort_desc: bool = True
):
    items = []
    try:
        from app.training.experiments.registry import global_experiment_registry
        exps = global_experiment_registry.list_experiments()
        for e in exps:
            d = e.to_dict()
            if dataset and d.get("dataset", "").lower() != dataset.lower(): continue
            if algorithm and d.get("algorithm", "").lower() != algorithm.lower(): continue
            if status and d.get("lifecycle_state", "").lower() != status.lower(): continue
            if tag and tag.lower() not in [t.lower() for t in d.get("tags", [])]: continue
            items.append(d)
            
        if items and sort_by in items[0]:
            items.sort(key=lambda x: x.get(sort_by, ""), reverse=sort_desc)
    except Exception: pass
    return paginate(items, page, size)

@router.get("/experiments/compare")
def compare_experiments(ids: str = Query(..., description="Comma separated experiment IDs")):
    from app.training.experiments.registry import global_experiment_registry
    from app.monitoring.audit import AuditLogger, AuditEvent
    exp_ids = [e.strip() for e in ids.split(",") if e.strip()]
    res = global_experiment_registry.compare(exp_ids)
    AuditLogger.record(AuditEvent(event_name="EXPERIMENT_COMPARED", component="ManagementAPI", severity="INFO", payload={"experiment_ids": exp_ids}))
    return res

@router.get("/experiments/{id}")
def get_experiment(id: str):
    from app.training.experiments.registry import global_experiment_registry
    from fastapi import HTTPException
    try:
        return global_experiment_registry.get(id).to_dict()
    except ValueError:
        raise HTTPException(status_code=404, detail="Experiment not found")

@router.get("/models/{id}/importance")
def get_model_importance(id: str):
    from app.serving.dependencies import _training_registry
    from fastapi import HTTPException
    try:
        meta = _training_registry.get(id)
        return {"model_id": id, "feature_importance": meta.feature_importance or {}}
    except Exception:
        raise HTTPException(status_code=404, detail="Model not found")

@router.get("/models/{id}/explanation")
def get_model_explanation(id: str):
    from app.serving.dependencies import _training_registry
    from fastapi import HTTPException
    try:
        meta = _training_registry.get(id)
        return {"model_id": id, "shap_summary": meta.shap_summary or {}}
    except Exception:
        raise HTTPException(status_code=404, detail="Model not found")

@router.get("/drift")
def get_drift_status(model_id: str = None):
    """Generates a live drift report for a specific model."""
    from app.serving.dependencies import _training_registry
    from app.monitoring.drift.engine import global_drift_engine
    from fastapi import HTTPException
    
    if not model_id:
        # Default to champion model if not specified
        try:
            aliases = _training_registry.list_aliases()
            if "default" in aliases:
                model_id = aliases["default"]
            else:
                raise HTTPException(status_code=400, detail="No model_id provided and no default alias found.")
        except Exception:
            raise HTTPException(status_code=400, detail="No model_id provided.")
            
    try:
        meta = _training_registry.get(model_id)
        report = global_drift_engine.generate_report(model_id, meta.baseline_profile)
        
        # Convert dataclass to dict
        from dataclasses import asdict
        report_dict = asdict(report)
        report_dict["timestamp"] = report.timestamp.isoformat()
        report_dict["severity"] = report.severity.value
        return report_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate drift report: {e}")

@router.get("/drift/history")
def get_drift_history():
    """Fetches historical drift alerts from the audit logger."""
    from app.monitoring.audit import AuditLogger
    logs = AuditLogger.get_logs(limit=100)
    drift_logs = [log for log in logs if log["event_name"] in ["DRIFT_DETECTED", "FEATURE_DRIFT", "MODEL_DRIFT"]]
    return {"history": drift_logs}

@router.get("/drift/{feature}")
def get_feature_drift(feature: str, model_id: str = None):
    """Gets drift specifically for one feature."""
    report = get_drift_status(model_id)
    feature_drift = [f for f in report.get("drifted_features", []) if f["feature"] == feature]
    return {"feature": feature, "drift": feature_drift[0] if feature_drift else None}
