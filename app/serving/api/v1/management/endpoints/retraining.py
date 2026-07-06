from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from app.training.retraining.manager import global_retraining_manager
from app.training.retraining.metadata import RetrainingTrigger

router = APIRouter(prefix="/retraining", tags=["retraining"])

class StartRetrainingRequest(BaseModel):
    dataset_name: str
    trigger_type: str = "MANUAL"

class RollbackRequest(BaseModel):
    dataset_name: str

@router.get("")
def list_retraining_jobs():
    """Lists all active and historical retraining jobs."""
    jobs = global_retraining_manager.list_jobs()
    return {"items": jobs}

@router.post("/start")
def start_retraining(req: StartRetrainingRequest):
    """Manually triggers a retraining job for a dataset."""
    try:
        trigger = RetrainingTrigger(req.trigger_type)
        job_id = global_retraining_manager.start_retraining(req.dataset_name, trigger)
        return {"job_id": job_id, "status": "STARTED"}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trigger type: {req.trigger_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rollback")
def rollback_model(req: RollbackRequest):
    """Rolls back the active model to a previous archived champion."""
    success = global_retraining_manager.rollback(req.dataset_name)
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed. No archived models found.")
    return {"status": "SUCCESS", "message": f"Rolled back model for dataset {req.dataset_name}"}

@router.get("/history")
def get_retraining_history():
    """Fetches historical retraining audit logs."""
    from app.monitoring.audit import AuditLogger
    logs = AuditLogger.get_logs(limit=100)
    retrain_logs = [log for log in logs if log["event_name"] in ["RETRAINING_STARTED", "RETRAINING_COMPLETED", "RETRAINING_FAILED", "CHAMPION_PROMOTED", "ROLLBACK_EXECUTED"]]
    return {"history": retrain_logs}
