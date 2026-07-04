"""
Assembles all management endpoints under a secured router.
"""
from fastapi import APIRouter, Depends
from .endpoints import overview_router, registries_router, pipelines_router, observability_router

def verify_admin_token():
    """
    Placeholder dependency for future JWT/RBAC integration.
    Currently allows all traffic.
    """
    return True

management_router = APIRouter(
    prefix="/management",
    tags=["management"],
    dependencies=[Depends(verify_admin_token)]
)

management_router.include_router(overview_router)
management_router.include_router(registries_router)
management_router.include_router(pipelines_router)
management_router.include_router(observability_router)
