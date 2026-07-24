from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: str
    username: str
    email: EmailStr
    status: str
    role: Optional[str]
    permissions: List[str]
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]


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


class SessionMetaResponse(BaseModel):
    id: str
    session_id: str
    device: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_revoked: bool
