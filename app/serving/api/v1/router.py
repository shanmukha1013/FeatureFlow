from fastapi import APIRouter, Depends
from app.serving.api.v1.endpoints import predict, health, models, version, features, model_cache, prediction_cache, explanations, data_quality
from app.serving.api.v1.endpoints import redis_observability, auth, users, api_keys, admin_security
from app.serving.api.v1.management.router import management_router
from app.security.dependencies import get_current_user

v1_router = APIRouter()

# Unprotected Authentication routes
v1_router.include_router(auth.router)

# Protected routes
protected = [Depends(get_current_user)]

v1_router.include_router(users.router, dependencies=protected)
v1_router.include_router(api_keys.router, dependencies=protected)
v1_router.include_router(admin_security.router, dependencies=protected)

v1_router.include_router(predict.router, tags=["predict"], dependencies=protected)
v1_router.include_router(health.router, tags=["health"], dependencies=protected)
v1_router.include_router(models.router, tags=["models"], dependencies=protected)
v1_router.include_router(version.router, tags=["version"], dependencies=protected)
v1_router.include_router(features.router, tags=["features"], dependencies=protected)
v1_router.include_router(model_cache.router, tags=["model_cache"], dependencies=protected)
v1_router.include_router(prediction_cache.router, tags=["prediction_cache"], dependencies=protected)
v1_router.include_router(redis_observability.router, tags=["redis_observability"], dependencies=protected)
v1_router.include_router(explanations.router, dependencies=protected)
v1_router.include_router(data_quality.router, prefix="/data-quality", tags=["data-quality"], dependencies=protected)

# Management router might have its own protection or we protect it fully here
v1_router.include_router(management_router, dependencies=protected)
