"""
Implements the model discovery endpoint.
Returns the active model routing table from the prediction engine.
"""
from fastapi import APIRouter, Depends
from app.serving.schemas.response import ModelsResponseSchema, ModelAliasSchema
from app.serving.dependencies import get_prediction_engine

router = APIRouter()


@router.get("/models", response_model=ModelsResponseSchema)
def list_models(engine=Depends(get_prediction_engine)):
    """
    Returns the current operational routing table of active models.
    """
    aliases_list = []
    for model_id, (mid, ver) in engine.routing_registry.items():
        aliases_list.append(ModelAliasSchema(alias=model_id, model_id=mid, version=ver))
    return ModelsResponseSchema(aliases=aliases_list)
