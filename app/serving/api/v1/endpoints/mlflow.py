from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.events import get_event_bus
from app.events.schema import Event, EventSeverity, EventType
from app.mlflow.schemas import (
    MLflowModelResponse,
    MLflowPromoteRequest,
    MLflowPromoteResponse,
    MLflowRunResponse,
    MLflowTrainRequest,
    MLflowTrainResponse,
)
from app.mlflow.service import MLflowService
from app.storage.database import get_db

router = APIRouter(prefix="/mlflow", tags=["mlflow"])


@router.post("/train", response_model=MLflowTrainResponse)
async def run_training(
    request: MLflowTrainRequest,
    db: AsyncSession = Depends(get_db)
):
    service = MLflowService(db)
    try:
        experiment = await service.run_training(
            dataset_id=request.dataset_id,
            algorithm=request.algorithm,
            hyperparameters=request.hyperparameters or {},
            target_column=request.target_column or "target"
        )

        # Emit event
        bus = get_event_bus()
        if bus:
            await bus.publish(Event(
                type=EventType.JOB_COMPLETED,
                source="mlflow.training",
                payload={
                    "run_id": experiment.mlflow_run_id,
                    "experiment_id": experiment.mlflow_experiment_id,
                    "algorithm": request.algorithm,
                    "dataset_id": request.dataset_id
                }
            ))

        return MLflowTrainResponse(
            run_id=experiment.mlflow_run_id or "",
            experiment_id=experiment.mlflow_experiment_id or "",
            status=experiment.status,
            metrics=experiment.metrics,
            parameters=experiment.parameters
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Training failed: {e}"
        )


@router.get("/experiments")
async def list_experiments(db: AsyncSession = Depends(get_db)):
    service = MLflowService(db)
    try:
        exps = service.get_experiments()
        return [{"experiment_id": e.experiment_id, "name": e.name, "lifecycle_stage": e.lifecycle_stage} for e in exps]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}", response_model=MLflowRunResponse)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    service = MLflowService(db)
    try:
        run = service.get_run(run_id)
        return MLflowRunResponse(
            run_id=run.info.run_id,
            experiment_id=run.info.experiment_id,
            status=run.info.status,
            metrics=run.data.metrics,
            params=run.data.params
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Run not found: {e}")


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    service = MLflowService(db)
    try:
        models = service.get_models()
        return [{"name": m.name, "creation_timestamp": m.creation_timestamp, "aliases": getattr(m, "aliases", {})} for m in models]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/promote", response_model=MLflowPromoteResponse)
async def promote_model(
    request: MLflowPromoteRequest,
    db: AsyncSession = Depends(get_db)
):
    service = MLflowService(db)
    try:
        service.promote_model(
            model_name=request.model_name,
            version=request.version,
            alias=request.alias
        )

        # Emit event
        bus = get_event_bus()
        if bus:
            await bus.publish(Event(
                type=EventType.MODEL_PROMOTED,
                source="mlflow.promotion",
                payload={
                    "model_name": request.model_name,
                    "version": request.version,
                    "alias": request.alias
                },
                severity=EventSeverity.INFO
            ))

        return MLflowPromoteResponse(
            model_name=request.model_name,
            version=request.version,
            alias=request.alias,
            status="PROMOTED"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Promotion failed: {e}"
        )


@router.get("/models/{name}/latest", response_model=MLflowModelResponse)
async def get_latest_model(name: str, db: AsyncSession = Depends(get_db)):
    service = MLflowService(db)
    model_info = service.get_latest_model(name)
    if not model_info:
        raise HTTPException(status_code=404, detail="Model not found")
    return MLflowModelResponse(**model_info)
