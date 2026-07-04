"""
Implements the model discovery endpoint.
"""
from fastapi import APIRouter, Depends
from app.serving.schemas.response import ModelsResponseSchema, ModelAliasSchema
from app.serving.dependencies import get_inference_registry

router = APIRouter()

@router.get("/models", response_model=ModelsResponseSchema)
def list_models(registry = Depends(get_inference_registry)):
    """
    Returns the current operational routing table of active models.
    """
    aliases = registry.list_aliases()
    models_list = [
        ModelAliasSchema(alias=alias, model_id=mid, version=ver)
        for alias, (mid, ver) in aliases.items()
    ]
    return ModelsResponseSchema(aliases=models_list)
