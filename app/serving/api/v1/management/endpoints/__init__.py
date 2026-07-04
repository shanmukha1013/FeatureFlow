"""
Exports management endpoints.
"""
from .overview import router as overview_router
from .registries import router as registries_router
from .pipelines import router as pipelines_router
from .observability import router as observability_router

__all__ = ["overview_router", "registries_router", "pipelines_router", "observability_router"]
