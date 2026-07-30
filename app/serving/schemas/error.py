"""
Pydantic contracts for standardized API errors.
"""
from typing import Any, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    error_code: str
    message: str
    details: Optional[Any] = None


class ErrorResponseSchema(BaseModel):
    """
    Standardized schema for all HTTP failures.
    """
    error: ErrorDetail
