from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.security.auth import get_api_key_hash
from app.storage.database import get_db
from app.storage.models import ApiKey
from app.utils.logger import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


async def verify_api_key(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> ApiKey:
    """
    Validates token from Authorization header.
    Only supports Platform API Keys (ff_xxx).
    """
    token = credentials.credentials

    if not token.startswith("ff_"):
        raise HTTPException(status_code=401, detail="Invalid API Key format")

    key_hash = get_api_key_hash(token)
    result = await db.execute(select(ApiKey).filter(ApiKey.key_hash == key_hash))
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if api_key.is_revoked:
        raise HTTPException(status_code=401, detail="API Key revoked")

    request.state.auth_method = "api_key"
    request.state.api_key_scopes = api_key.scopes

    return api_key


class RequirePermission:
    def __init__(self, action: str, resource: str):
        self.action = action
        self.resource = resource

    async def __call__(self, request: Request, api_key: ApiKey = Depends(verify_api_key)):
        # For API keys with fine-grained scopes
        scopes = getattr(request.state, "api_key_scopes", None)
        req_scope = f"{self.action}:{self.resource}"

        if scopes is not None:
            if req_scope not in scopes and "*" not in scopes:
                raise HTTPException(status_code=403, detail="API Key lacks required scope")
        return api_key


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
