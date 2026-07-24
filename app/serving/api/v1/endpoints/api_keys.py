from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
import datetime as dt

from app.storage.database import get_db
from app.storage.models import User, ApiKey
from app.security.auth import generate_api_key
from app.security.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyMetaResponse
from app.security.dependencies import get_current_user
from app.monitoring.audit import AuditLogger, AuditEvent

router = APIRouter(prefix="/api-keys", tags=["api_keys"])


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(request: ApiKeyCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    raw_key, key_hash = generate_api_key()

    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + dt.timedelta(days=request.expires_in_days)

    api_key = ApiKey(
        user_id=user.id,
        name=request.name,
        key_hash=key_hash,
        scopes=request.scopes,
        expires_at=expires_at
    )
    db.add(api_key)

    await AuditLogger.record(db, AuditEvent(
        event_name="API_KEY_CREATED", component="AuthAPI", severity="INFO",
        payload={"user_id": user.id, "key_name": request.name}
    ))
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        api_key=raw_key,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at
    )


@router.get("", response_model=list[ApiKeyMetaResponse])
async def list_api_keys(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).filter(ApiKey.user_id == user.id))
    keys = result.scalars().all()
    return [ApiKeyMetaResponse(
        id=k.id, name=k.name, scopes=k.scopes, expires_at=k.expires_at,
        created_at=k.created_at, last_used_at=k.last_used_at, is_revoked=k.is_revoked
    ) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id))
    key = result.scalars().first()
    if key:
        key.is_revoked = True
        await AuditLogger.record(db, AuditEvent(
            event_name="API_KEY_REVOKED", component="AuthAPI", severity="INFO",
            payload={"user_id": user.id, "key_id": key_id}
        ))
        await db.commit()
    return
