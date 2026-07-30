"""
Exports management endpoints.
"""
from .datasets import router as datasets_router
from .lineage import router as lineage_router
from .observability import router as observability_router
from .overview import router as overview_router
from .pipelines import router as pipelines_router
from .registries import router as registries_router

__all__ = ["overview_router", "registries_router", "pipelines_router", "observability_router", "datasets_router", "lineage_router"]
