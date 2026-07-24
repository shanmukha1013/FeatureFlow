"""
Assembles all management endpoints under a secured router.
"""
from fastapi import APIRouter, Depends
from .endpoints import overview_router, registries_router, pipelines_router, observability_router
from .endpoints.retraining import router as retraining_router
from .endpoints.enterprise import router as enterprise_router
from app.security.dependencies import RequireRole, get_current_user

management_router = APIRouter(
    prefix="/management",
    tags=["management"],
    dependencies=[Depends(get_current_user), Depends(RequireRole(["ADMIN", "ML_ENGINEER"]))]
)

management_router.include_router(overview_router)
management_router.include_router(registries_router, prefix="/registries")
management_router.include_router(registries_router)  # backward compatibility for /management/datasets
management_router.include_router(pipelines_router, prefix="/pipelines")
management_router.include_router(pipelines_router)  # backward compatibility for /management/pipelines
management_router.include_router(observability_router, prefix="/observability")
management_router.include_router(observability_router)  # backward compatibility for /management/audit
management_router.include_router(retraining_router)
management_router.include_router(enterprise_router)
