"""
Implements the version reporting endpoint.
"""
from fastapi import APIRouter
from app.serving.schemas.response import VersionResponseSchema
from app.serving.config import serving_config

router = APIRouter()

@router.get("/version", response_model=VersionResponseSchema)
def get_version():
    """
    Returns the current semantic version of the platform and API API.
    """
    return VersionResponseSchema(
        platform_version=serving_config.platform_version,
        api_version=serving_config.api_version
    )
