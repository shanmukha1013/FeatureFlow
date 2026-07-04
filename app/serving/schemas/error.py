"""
Pydantic contracts for standardized API errors.
"""
from pydantic import BaseModel
from typing import Optional, Any

class ErrorDetail(BaseModel):
    error_code: str
    message: str
    details: Optional[Any] = None

class ErrorResponseSchema(BaseModel):
    """
    Standardized schema for all HTTP failures.
    """
    error: ErrorDetail
