from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select

from app.storage.database import get_db
from app.storage.models import User, UserSession, AuditLog
from app.security.dependencies import RequireRole

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db), _: User = Depends(RequireRole(["ADMIN"]))):
    total_users_res = await db.execute(select(func.count(User.id)))
    active_sessions_res = await db.execute(select(func.count(UserSession.id)).filter(UserSession.is_revoked.is_(False)))
    locked_users_res = await db.execute(select(func.count(User.id)).filter(User.status == "LOCKED"))
    failed_logins_res = await db.execute(select(func.count(AuditLog.id)).filter(AuditLog.event_name == "LOGIN_FAILED"))

    return {
        "total_users": total_users_res.scalar(),
        "active_sessions": active_sessions_res.scalar(),
        "locked_users": locked_users_res.scalar(),
        "failed_logins": failed_logins_res.scalar()
    }


@router.get("/sessions")
async def get_all_sessions(db: AsyncSession = Depends(get_db), _: User = Depends(RequireRole(["ADMIN"]))):
    result = await db.execute(select(UserSession).order_by(UserSession.created_at.desc()).limit(100))
    sessions = result.scalars().all()
    return [{"id": s.id, "user_id": s.user_id, "ip": s.ip_address, "device": s.device, "revoked": s.is_revoked} for s in sessions]


@router.get("/locked-users")
async def get_locked_users(db: AsyncSession = Depends(get_db), _: User = Depends(RequireRole(["ADMIN"]))):
    result = await db.execute(select(User).filter(User.status == "LOCKED"))
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username, "locked_until": u.account_locked_until} for u in users]
