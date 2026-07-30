"""
Generic pagination wrapper for list endpoints.
"""
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    has_next: bool
