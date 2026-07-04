"""
Exposes read-only access to platform registries.
"""
from fastapi import APIRouter, Query
from typing import Any, List
from app.serving.api.v1.management.schemas.pagination import PaginatedResponse

router = APIRouter()

def paginate(items: List[Any], page: int, size: int) -> PaginatedResponse[Any]:
    total = len(items)
    start = (page - 1) * size
    end = start + size
    sliced = items[start:end]
    has_next = end < total
    return PaginatedResponse(items=sliced, total=total, page=page, size=size, has_next=has_next)

@router.get("/datasets", response_model=PaginatedResponse[Any])
def get_datasets(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100)):
    items = []
    try:
        from app.data.flexy_registry import registry
        if hasattr(registry, "schemas"):
            items = [s.__dict__ if hasattr(s, '__dict__') else str(s) for s in registry.schemas.values()]
    except Exception:
        pass
    return paginate(items, page, size)

@router.get("/features", response_model=PaginatedResponse[Any])
def get_features(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100)):
    items = []
    try:
        from app.features.registry import global_feature_registry
        for name in global_feature_registry.list_features():
            feat = global_feature_registry.get(name)
            if hasattr(feat, "metadata"):
                items.append(feat.metadata.__dict__)
            else:
                items.append({"name": name})
    except Exception:
        pass
    return paginate(items, page, size)

@router.get("/models", response_model=PaginatedResponse[Any])
def get_models(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100), status: str = None):
    items = []
    try:
        from app.serving.dependencies import _training_registry
        model_ids = _training_registry.list_models()
        for mid in model_ids:
            meta = _training_registry.get(mid)
            if status:
                if getattr(meta, "lifecycle_state", None) == status:
                    items.append(meta.to_dict())
            else:
                items.append(meta.to_dict())
    except Exception:
        pass
    return paginate(items, page, size)
