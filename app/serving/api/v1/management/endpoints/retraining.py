from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.storage.database import get_db
from app.monitoring.audit import AuditLogger, AuditEvent

router = APIRouter(prefix="/retraining", tags=["retraining"])


class StartRetrainingRequest(BaseModel):
    dataset_name: str
    trigger_type: str = "MANUAL"


class RollbackRequest(BaseModel):
    dataset_name: str


@router.get("")
async def list_retraining_jobs(session: AsyncSession = Depends(get_db)):
    """Lists all active and historical retraining jobs."""
    from app.storage.models import AuditLog
    query = select(AuditLog).filter(
        AuditLog.event_name.in_(["RETRAINING_STARTED", "RETRAINING_COMPLETED", "RETRAINING_FAILED"])
    ).order_by(desc(AuditLog.created_at)).limit(50)

    res = await session.execute(query)
    logs = res.scalars().all()

    items = []
    for log in logs:
        items.append({
            "job_id": log.payload.get("job_id") if log.payload else None,
            "dataset_name": log.payload.get("dataset") if log.payload else None,
            "status": log.event_name.split("_")[1] if "_" in log.event_name else log.event_name,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "details": log.payload
        })
    return {"items": items}


async def execute_retraining_task(dataset_name: str, trigger_type: str):
    import uuid
    job_id = f"job_{uuid.uuid4().hex[:6]}"

    # Needs a dedicated session since it's a background task
    from app.storage.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await AuditLogger.record(session, AuditEvent("RETRAINING_STARTED", "RetrainingAPI", "INFO", {"job_id": job_id, "dataset": dataset_name, "trigger": trigger_type}))

        try:
            from app.storage.repositories.core import DatasetRepository
            from app.training.orchestrator import TrainingOrchestrator

            repo = DatasetRepository(session)
            dataset = await repo.get_by_name(dataset_name)

            if not dataset:
                raise ValueError(f"Dataset {dataset_name} not found")

            orchestrator = TrainingOrchestrator()
            await orchestrator.execute(session, dataset)

            await AuditLogger.record(session, AuditEvent("RETRAINING_COMPLETED", "RetrainingAPI", "INFO", {"job_id": job_id, "dataset": dataset_name}))
            await session.commit()
        except Exception as e:
            await session.rollback()
            await AuditLogger.record(session, AuditEvent("RETRAINING_FAILED", "RetrainingAPI", "ERROR", {"job_id": job_id, "dataset": dataset_name, "error": str(e)}))
            await session.commit()


@router.post("/start")
async def start_retraining(req: StartRetrainingRequest, background_tasks: BackgroundTasks):
    """Manually triggers a retraining job for a dataset."""
    background_tasks.add_task(execute_retraining_task, req.dataset_name, req.trigger_type)
    return {"status": "STARTED", "message": "Retraining job queued in background."}


@router.post("/rollback")
async def rollback_model(req: RollbackRequest, session: AsyncSession = Depends(get_db)):
    """Rolls back the active model to a previous archived champion."""
    from app.storage.models import Dataset, Model, ChampionModel
    
    # 1. Find the dataset
    ds_res = await session.execute(select(Dataset).filter(Dataset.name == req.dataset_name))
    dataset = ds_res.scalars().first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    # 2. Get the current champion
    champ_res = await session.execute(select(ChampionModel).filter(ChampionModel.dataset_id == dataset.id))
    current_champ = champ_res.scalars().first()
    
    # 3. Find the previous model
    query = select(Model).filter(Model.dataset_id == dataset.id).order_by(desc(Model.created_at))
    models_res = await session.execute(query)
    models = models_res.scalars().all()
    
    if len(models) < 2:
        raise HTTPException(status_code=400, detail="Not enough models to rollback. Need at least 2.")
        
    # Identify the rollback target (the newest model that is not the current champion)
    target_model = None
    for m in models:
        if not current_champ or m.id != current_champ.model_id:
            target_model = m
            break
            
    if not target_model:
        raise HTTPException(status_code=400, detail="No valid previous model found.")
        
    # 4. Perform Rollback
    if current_champ:
        current_champ.model_id = target_model.id
    else:
        current_champ = ChampionModel(dataset_id=dataset.id, model_id=target_model.id, status="ACTIVE")
        session.add(current_champ)
        
    # Update statuses
    if current_champ:
        old_champ_model_res = await session.execute(select(Model).filter(Model.id == current_champ.model_id))
        old_champ = old_champ_model_res.scalars().first()
        if old_champ:
            old_champ.status = "ARCHIVED"
            
    target_model.status = "CHAMPION"
    
    await AuditLogger.record(session, AuditEvent("ROLLBACK_EXECUTED", "RetrainingAPI", "WARNING", {"dataset": req.dataset_name, "rolled_back_to": target_model.id}))
    await session.commit()
    
    return {"status": "SUCCESS", "message": f"Rolled back to model {target_model.id}"}


@router.get("/history")
async def get_retraining_history(session: AsyncSession = Depends(get_db)):
    """Fetches historical retraining audit logs."""
    from app.storage.models import AuditLog
    query = select(AuditLog).filter(
        AuditLog.event_name.in_(["RETRAINING_STARTED", "RETRAINING_COMPLETED", "RETRAINING_FAILED", "CHAMPION_PROMOTED", "ROLLBACK_EXECUTED"])
    ).order_by(desc(AuditLog.created_at)).limit(100)

    res = await session.execute(query)
    logs = res.scalars().all()

    return {"history": [
        {"timestamp": log_entry.created_at.isoformat() if log_entry.created_at else None, "event": log_entry.event_name, "payload": log_entry.payload}
        for log_entry in logs
    ]}
