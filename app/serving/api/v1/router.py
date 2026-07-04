from fastapi import APIRouter
from app.serving.api.v1.endpoints import predict, health, models, version
from app.serving.api.v1.management.router import management_router

v1_router = APIRouter()

v1_router.include_router(predict.router, tags=["predict"])
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(models.router, tags=["models"])
v1_router.include_router(version.router, tags=["version"])
v1_router.include_router(management_router)
