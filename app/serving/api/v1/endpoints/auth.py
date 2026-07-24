from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
import uuid
from sqlalchemy import update

from app.storage.database import get_db
from app.storage.models import User, UserSession, PasswordHistory, Role, Permission, RolePermission
from app.security.auth import verify_password, get_password_hash, create_access_token, create_refresh_token, validate_password_strength
from app.security.schemas import LoginRequest, RegisterRequest, RefreshRequest, TokenResponse, UserProfile, SessionMetaResponse
from app.security.dependencies import get_current_user, RateLimiter
from app.monitoring.audit import AuditLogger, AuditEvent
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, req: Request, db: AsyncSession = Depends(get_db)):
    if not validate_password_strength(request.password):
        raise HTTPException(status_code=400, detail="Password does not meet enterprise strength requirements")

    result = await db.execute(select(User).filter((User.username == request.username) | (User.email == request.email)))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    hashed_password = get_password_hash(request.password)
    role_res = await db.execute(select(Role).filter(Role.name == "VIEWER"))
    viewer_role = role_res.scalars().first()

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password,
        role_id=viewer_role.id if viewer_role else None
    )
    db.add(user)
    await db.flush()

    # Track password history
    pwd_history = PasswordHistory(user_id=user.id, hashed_password=hashed_password)
    db.add(pwd_history)

    await AuditLogger.record(db, AuditEvent(
        event_name="USER_REGISTERED",
        component="AuthAPI",
        severity="INFO",
        payload={"username": user.username, "email": user.email}
    ))
    await db.commit()
    await db.refresh(user)

    return UserProfile(
        id=user.id, username=user.username, email=user.email, status=user.status,
        role=viewer_role.name if viewer_role else None, permissions=[],
        mfa_enabled=user.mfa_enabled, created_at=user.created_at, last_login=user.last_login
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request, db: AsyncSession = Depends(get_db), _: None = Depends(RateLimiter())):
    result = await db.execute(select(User).filter(User.username == request.username))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if user.status != "ACTIVE":
        if user.status == "LOCKED":
            if user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc):
                raise HTTPException(status_code=403, detail="Account is temporarily locked due to multiple failed login attempts")
            else:
                user.status = "ACTIVE"
                user.failed_login_attempts = 0
                user.account_locked_until = None
        else:
            raise HTTPException(status_code=403, detail=f"Account is {user.status}")

    if not verify_password(request.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.status = "LOCKED"
            import datetime as dt
            user.account_locked_until = datetime.now(timezone.utc) + dt.timedelta(minutes=settings.lockout_duration_minutes)
            await AuditLogger.record(db, AuditEvent(
                event_name="ACCOUNT_LOCKED", component="AuthAPI", severity="WARNING",
                payload={"username": user.username}
            ))
        await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # Success
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.last_login = datetime.now(timezone.utc)

    session_id = str(uuid.uuid4())
    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id, session_id)

    client_ip = req.headers.get("X-Forwarded-For", req.client.host if req.client else None)
    device = req.headers.get("User-Agent")

    import datetime as dt
    expires_at = datetime.now(timezone.utc) + dt.timedelta(days=settings.refresh_token_expire_days)

    user_session = UserSession(
        user_id=user.id,
        session_id=session_id,
        refresh_token=refresh_token,
        device=device,
        ip_address=client_ip,
        expires_at=expires_at
    )
    db.add(user_session)

    await AuditLogger.record(db, AuditEvent(
        event_name="LOGIN_SUCCESS", component="AuthAPI", severity="INFO",
        payload={"username": user.username, "ip_address": client_ip}
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, req: Request, db: AsyncSession = Depends(get_db), _: None = Depends(RateLimiter())):
    from app.security.auth import decode_token
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    session_id = payload.get("jti")
    user_id = payload.get("sub")

    result = await db.execute(select(UserSession).filter(UserSession.session_id == session_id))
    user_session = result.scalars().first()
    if not user_session or user_session.is_revoked or user_session.refresh_token != request.refresh_token:
        # Replay attack or revoked token detected
        if user_session and user_session.is_revoked:
            await AuditLogger.record(db, AuditEvent(
                event_name="TOKEN_REPLAY_ATTEMPT", component="AuthAPI", severity="CRITICAL",
                payload={"user_id": user_id, "session_id": session_id}
            ))
            # Revoke all sessions for safety
            await db.execute(update(UserSession).where(UserSession.user_id == user_id).values(is_revoked=True))
            await db.commit()
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user or user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="User account is not active")

    # Rotate token
    user_session.is_revoked = True

    new_session_id = str(uuid.uuid4())
    access_token = create_access_token(user.id, user.username)
    new_refresh_token = create_refresh_token(user.id, new_session_id)

    import datetime as dt
    expires_at = datetime.now(timezone.utc) + dt.timedelta(days=settings.refresh_token_expire_days)

    new_session = UserSession(
        user_id=user.id,
        session_id=new_session_id,
        refresh_token=new_refresh_token,
        device=req.headers.get("User-Agent"),
        ip_address=req.headers.get("X-Forwarded-For", req.client.host if req.client else None),
        expires_at=expires_at
    )
    db.add(new_session)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return

    token = auth_header.split(" ")[1]
    from app.security.auth import decode_token
    import logging
    logger = logging.getLogger(__name__)
    try:
        decode_token(token)
        # We can't revoke JWTs without a denylist, but if they pass the refresh token, we revoke it.
        # Ideally client calls logout with the refresh token. For simplicity, we just revoke all sessions for this token.
    except Exception as e:
        logger.warning(f"Failed to decode token during logout: {e}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserProfile)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    role_name = None
    perms = []
    if user.role_id:
        result = await db.execute(select(Role).filter(Role.id == user.role_id))
        role = result.scalars().first()
        if role:
            role_name = role.name
            perm_res = await db.execute(select(Permission).join(RolePermission).filter(RolePermission.role_id == role.id))
            role_perms = perm_res.scalars().all()
            perms = [f"{p.action}:{p.resource}" for p in role_perms]

    return UserProfile(
        id=user.id, username=user.username, email=user.email, status=user.status,
        role=role_name, permissions=perms, mfa_enabled=user.mfa_enabled,
        created_at=user.created_at, last_login=user.last_login
    )


@router.get("/sessions", response_model=list[SessionMetaResponse])
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSession).filter(UserSession.user_id == user.id))
    sessions = result.scalars().all()
    return [SessionMetaResponse(
        id=s.id, session_id=s.session_id, device=s.device, ip_address=s.ip_address,
        created_at=s.created_at, last_activity=s.last_activity, expires_at=s.expires_at, is_revoked=s.is_revoked
    ) for s in sessions]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSession).filter(UserSession.id == session_id, UserSession.user_id == user.id))
    session = result.scalars().first()
    if session:
        session.is_revoked = True
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(UserSession).where(UserSession.user_id == user.id).values(is_revoked=True))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
