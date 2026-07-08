"""
Provides high-level platform and system overview data.
"""
import sys
import platform
import fastapi
from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.storage.database import get_db
from app.storage.models import Dataset, Feature, Model, Experiment
from app.serving.api.v1.management.schemas.responses import (
    PlatformOverviewSchema, SystemInfoSchema, StatisticsSchema, AboutSchema, ConfigSchema
)
from app.monitoring.health import HealthMonitor
from app.serving.config import serving_config

router = APIRouter()

@router.get("/platform", response_model=PlatformOverviewSchema)
async def get_platform_overview(session: AsyncSession = Depends(get_db)):
    health = HealthMonitor.check_health()
    
    # Compute from database
    result_datasets = await session.execute(select(func.count(Dataset.id)))
    num_datasets = result_datasets.scalar_one()
    
    result_features = await session.execute(select(func.count(Feature.id)))
    num_features = result_features.scalar_one()
    
    result_models = await session.execute(select(func.count(Model.id)))
    num_models = result_models.scalar_one()
    
    result_experiments = await session.execute(select(func.count(Experiment.id)))
    num_pipelines = result_experiments.scalar_one()

    return PlatformOverviewSchema(
        platform_version=serving_config.platform_version,
        health=health.status.value,
        registered_models=num_models,
        registered_features=num_features,
        registered_datasets=num_datasets,
        pipeline_count=num_pipelines,
        training_jobs=num_pipelines,
        serving_status="ACTIVE",
        monitoring_status="ACTIVE",
        inference_status="ACTIVE"
    )

@router.get("/system", response_model=SystemInfoSchema)
async def get_system_info():
    return SystemInfoSchema(
        python_version=sys.version.split(" ")[0],
        operating_system=platform.system(),
        framework_version=fastapi.__version__,
        storage_backend="postgresql",
        monitoring_backend="postgresql",
        inference_backend="sklearn",
        training_backend="sklearn"
    )

@router.get("/statistics", response_model=StatisticsSchema)
async def get_statistics(session: AsyncSession = Depends(get_db)):
    total_preds = 0
    avg_latency = 0.0
    val_failures = 0
    
    from app.storage.models import AuditLog
    
    # Total Predictions
    pred_res = await session.execute(select(AuditLog).filter(AuditLog.event_name == 'PREDICTION_FINISHED'))
    preds = pred_res.scalars().all()
    total_preds = len(preds)
    
    if total_preds > 0:
        total_time = sum([p.payload.get("latency_ms", 0) for p in preds if p.payload])
        avg_latency = total_time / total_preds
        
    # Validation Failures
    val_res = await session.execute(select(AuditLog).filter(AuditLog.event_name == 'VALIDATION_FAILED'))
    val_failures = len(val_res.scalars().all())
        
    result_models = await session.execute(select(func.count(Model.id)))
    num_models = result_models.scalar_one()
    
    result_pipelines = await session.execute(select(func.count(Experiment.id)))
    num_pipelines = result_pipelines.scalar_one()
    
    return StatisticsSchema(
        total_predictions=total_preds,
        average_latency=avg_latency,
        training_count=num_models,
        pipeline_count=num_pipelines,
        inference_count=total_preds,
        validation_failures=val_failures
    )

@router.get("/about", response_model=AboutSchema)
async def get_about():
    return AboutSchema(
        platform_name="FeatureFlow",
        description="Production ML Platform (PostgreSQL Backed)",
        version=serving_config.platform_version,
        author="ML Platform Team",
        license="Internal",
        repository="internal/featureflow",
        build_timestamp=datetime.utcnow().isoformat()
    )

@router.get("/config", response_model=ConfigSchema)
async def get_config():
    return ConfigSchema(
        storage_backend="postgresql",
        monitoring_backend="postgresql",
        training_backend="sklearn",
        inference_backend="sklearn",
        serving_version=serving_config.api_version,
        enabled_modules=["data", "features", "storage", "pipeline", "training", "inference", "serving", "monitoring"]
    )
