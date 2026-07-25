from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ApiKeyCreate(BaseModel):
    name: str
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    api_key: str  # ONLY RETURNED ONCE
    scopes: Optional[List[str]]
    expires_at: Optional[datetime]


class ApiKeyMetaResponse(BaseModel):
    id: str
    name: str
    scopes: Optional[List[str]]
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]
    is_revoked: bool
