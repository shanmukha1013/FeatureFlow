"""
Provides high-level platform and system overview data.
"""
import sys
import platform
import fastapi
from fastapi import APIRouter
from datetime import datetime

from app.serving.api.v1.management.schemas.responses import (
    PlatformOverviewSchema, SystemInfoSchema, StatisticsSchema, AboutSchema, ConfigSchema
)
from app.monitoring.health import HealthMonitor
from app.serving.config import serving_config

router = APIRouter()

@router.get("/platform", response_model=PlatformOverviewSchema)
def get_platform_overview():
    health = HealthMonitor.check_health()
    
    # Compute from registries
    num_models = 0
    num_features = 0
    num_datasets = 0
    num_pipelines = 0
    
    try:
        from app.serving.dependencies import _training_registry
        num_models = len(_training_registry.list_models())
    except Exception: pass
    
    try:
        from app.features.registry import global_feature_registry
        num_features = len(global_feature_registry.list_features())
    except Exception: pass
    
    try:
        from app.data.flexy_registry import registry
        num_datasets = len(getattr(registry, "schemas", {}))
    except Exception: pass
    
    try:
        from app.pipelines.pipeline import _pipeline_history
        num_pipelines = len(_pipeline_history)
    except Exception: pass

    return PlatformOverviewSchema(
        platform_version=serving_config.platform_version,
        health=health.status.value,
        registered_models=num_models,
        registered_features=num_features,
        registered_datasets=num_datasets,
        pipeline_count=num_pipelines,
        training_jobs=num_models, # Roughly matches for now
        serving_status="ACTIVE",
        monitoring_status="ACTIVE",
        inference_status="ACTIVE"
    )

@router.get("/system", response_model=SystemInfoSchema)
def get_system_info():
    return SystemInfoSchema(
        python_version=sys.version.split(" ")[0],
        operating_system=platform.system(),
        framework_version=fastapi.__version__,
        storage_backend="local",
        monitoring_backend="local",
        inference_backend="sklearn",
        training_backend="sklearn"
    )

@router.get("/statistics", response_model=StatisticsSchema)
def get_statistics():
    total_preds = 0
    avg_latency = 0.0
    val_failures = 0
    
    try:
        from app.monitoring.metrics import _backend
        if hasattr(_backend, "counters"):
            # The exact counter keys depend on the strings used in monitoring interceptors
            total_preds = _backend.counters.get("http_requests_total_{'status': '200'}", 0)
            val_failures = _backend.counters.get("http_requests_total_{'status': '422'}", 0)
            
        if hasattr(_backend, "histograms"):
            latencies = _backend.histograms.get("http_request_latency_ms_{'endpoint': '/api/v1/predict'}", [])
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
    except Exception:
        pass
        
    num_models = 0
    try:
        from app.serving.dependencies import _training_registry
        num_models = len(_training_registry.list_models())
    except Exception: pass
    
    num_pipelines = 0
    try:
        from app.pipelines.pipeline import _pipeline_history
        num_pipelines = len(_pipeline_history)
    except Exception: pass
    
    return StatisticsSchema(
        total_predictions=total_preds,
        average_latency=avg_latency,
        training_count=num_models,
        pipeline_count=num_pipelines,
        inference_count=total_preds,
        validation_failures=val_failures
    )

@router.get("/about", response_model=AboutSchema)
def get_about():
    return AboutSchema(
        platform_name="FeatureFlow",
        description="Production ML Platform",
        version=serving_config.platform_version,
        author="ML Platform Team",
        license="Internal",
        repository="internal/featureflow",
        build_timestamp=datetime.utcnow().isoformat()
    )

@router.get("/config", response_model=ConfigSchema)
def get_config():
    return ConfigSchema(
        storage_backend="local",
        monitoring_backend="local",
        training_backend="sklearn",
        inference_backend="sklearn",
        serving_version=serving_config.api_version,
        enabled_modules=["data", "features", "storage", "pipeline", "training", "inference", "serving", "monitoring"]
    )
