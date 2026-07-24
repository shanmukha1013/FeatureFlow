"""
Maps internal domain exceptions to safe HTTP responses.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from app.inference.exceptions import InputValidationError, ModelLoadError, InferenceError


async def validation_error_handler(request: Request, exc: InputValidationError):
    """Handles 422 Unprocessable Entity - Bad feature vectors."""
    return JSONResponse(
        status_code=422,
        content={"error": {"error_code": "VALIDATION_ERROR", "message": str(exc)}}
    )


async def not_found_error_handler(request: Request, exc: InferenceError):
    """Handles 404 Not Found - Unknown aliases."""
    return JSONResponse(
        status_code=404,
        content={"error": {"error_code": "NOT_FOUND", "message": str(exc)}}
    )


async def service_unavailable_handler(request: Request, exc: ModelLoadError):
    """Handles 503 Service Unavailable - Artifacts corrupted or missing."""
    return JSONResponse(
        status_code=503,
        content={"error": {"error_code": "SERVICE_UNAVAILABLE", "message": str(exc)}}
    )


async def internal_error_handler(request: Request, exc: Exception):
    """Handles 500 Internal Server Error - Unexpected crashes."""
    return JSONResponse(
        status_code=500,
        content={"error": {"error_code": "INTERNAL_ERROR", "message": str(exc)}}
    )
