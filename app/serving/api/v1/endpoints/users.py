from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.storage.database import get_db
from app.storage.models import User, Role
from app.security.dependencies import RequireRole
from app.security.schemas import UserProfile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserProfile])
async def list_users(db: AsyncSession = Depends(get_db), _: User = Depends(RequireRole(["ADMIN"]))):
    result = await db.execute(select(User))
    users = result.scalars().all()
    profiles = []
    for user in users:
        role_name = None
        perms = []
        if user.role_id:
            role_res = await db.execute(select(Role).filter(Role.id == user.role_id))
            role = role_res.scalars().first()
            if role:
                role_name = role.name
        profiles.append(UserProfile(
            id=user.id, username=user.username, email=user.email, status=user.status,
            role=role_name, permissions=perms, mfa_enabled=user.mfa_enabled,
            created_at=user.created_at, last_login=user.last_login
        ))
    return profiles


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(RequireRole(["ADMIN"]))):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if user:
        await db.delete(user)
        await db.commit()
    return
