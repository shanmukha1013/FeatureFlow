from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.storage.database import get_db
from app.storage.models import User, Role, Permission, RolePermission, ApiKey
from app.security.auth import decode_token, get_api_key_hash
from app.utils.logger import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> User:
    """
    Validates token from Authorization header.
    Supports both JWT Access Tokens and API Keys (ff_xxx).
    """
    token = credentials.credentials

    if token.startswith("ff_"):
        # API Key flow
        key_hash = get_api_key_hash(token)
        result = await db.execute(select(ApiKey).filter(ApiKey.key_hash == key_hash))
        api_key = result.scalars().first()

        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        if api_key.is_revoked:
            raise HTTPException(status_code=401, detail="API Key revoked")

        result = await db.execute(select(User).filter(User.id == api_key.user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="API Key user not found")

        request.state.auth_method = "api_key"
        request.state.api_key_scopes = api_key.scopes

    else:
        # JWT flow
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalars().first()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")

            request.state.auth_method = "jwt"
            request.state.api_key_scopes = None

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Universal user checks
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail=f"User account is {user.status}")

    return user


class RequireRole:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        if not user.role_id:
            raise HTTPException(status_code=403, detail="User has no role")

        result = await db.execute(select(Role).filter(Role.id == user.role_id))
        role = result.scalars().first()
        if not role or role.name not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user


class RequirePermission:
    def __init__(self, action: str, resource: str):
        self.action = action
        self.resource = resource

    async def __call__(self, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        # For API keys with fine-grained scopes
        scopes = getattr(request.state, "api_key_scopes", None)
        req_scope = f"{self.action}:{self.resource}"

        if scopes is not None:
            if req_scope not in scopes and "*" not in scopes:
                raise HTTPException(status_code=403, detail="API Key lacks required scope")
            return user

        # Standard RBAC flow
        if not user.role_id:
            raise HTTPException(status_code=403, detail="User has no role")

        # Fetch permissions for user's role
        result = await db.execute(
            select(Permission).join(RolePermission).filter(
                RolePermission.role_id == user.role_id,
                Permission.action == self.action,
                Permission.resource == self.resource
            )
        )
        permissions = result.scalars().first()

        if not permissions:
            # Check if they have wildcard resource access
            result = await db.execute(
                select(Permission).join(RolePermission).filter(
                    RolePermission.role_id == user.role_id,
                    Permission.action == self.action,
                    Permission.resource == "*"
                )
            )
            wildcard_res = result.scalars().first()
            if not wildcard_res:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

        return user


class RateLimiter:
    """Redis-backed rate limiter to prevent brute force attacks."""

    def __init__(self, requests: int = 5, window: int = 60):
        self.requests = requests
        self.window = window

    async def __call__(self, request: Request):
        from app.cache.redis_client import get_redis_client
        redis_client = get_redis_client()

        # Use X-Forwarded-For if behind a proxy, otherwise client.host
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "127.0.0.1")
        key = f"rate_limit:{request.url.path}:{client_ip}"

        async def _incr_expire(client):
            p = client.pipeline()
            p.incr(key)
            p.expire(key, self.window, nx=True)
            return await p.execute()

        try:
            result = await redis_client.execute_with_retry(_incr_expire)
            if result and result[0] > self.requests:
                raise HTTPException(status_code=429, detail="Too many requests")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"RateLimiter failed (fail-open): {e}")
            pass  # Fail open if Redis is down
