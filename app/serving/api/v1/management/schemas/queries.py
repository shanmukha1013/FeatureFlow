"""
Query schemas for filtering and pagination.
"""
from pydantic import BaseModel, Field
from typing import Optional


class PaginationQuery(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=100)
    sort_by: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None
