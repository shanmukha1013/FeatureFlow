from fastapi import APIRouter
from app.serving.api.v1.endpoints import predict, health, models, version, features, model_cache, prediction_cache, explanations, data_quality, monitoring, mlflow
from app.serving.api.v1.endpoints import redis_observability, api_keys
from app.serving.api.v1.management.router import management_router

v1_router = APIRouter()

v1_router.include_router(api_keys.router)

v1_router.include_router(predict.router, tags=["predict"])
v1_router.include_router(health.router, tags=["health"])  # Unprotected for Render probes
v1_router.include_router(models.router, tags=["models"])
v1_router.include_router(version.router, tags=["version"])
v1_router.include_router(features.router, tags=["features"])
v1_router.include_router(model_cache.router, tags=["model_cache"])
v1_router.include_router(prediction_cache.router, tags=["prediction_cache"])
v1_router.include_router(redis_observability.router, tags=["redis_observability"])
v1_router.include_router(explanations.router)
v1_router.include_router(data_quality.router, prefix="/data-quality", tags=["data-quality"])
v1_router.include_router(monitoring.router)
v1_router.include_router(mlflow.router)

v1_router.include_router(management_router)
