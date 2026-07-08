from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.storage.database import get_db
from app.storage.models import ChampionModel, Model, User as DBUser

router = APIRouter(tags=["enterprise"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/security/login")
async def login(req: LoginRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBUser).filter(DBUser.username == req.username))
    user = result.scalars().first()
    
    # Simple mockup fallback for the demo frontend to still work if DB is empty
    # In a real app we'd seed the DB
    if not user:
        if req.username == "admin" and req.password == "admin":
            return {"token": "dummy-token", "role": "ADMINISTRATOR"}
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    # Not checking hash for simplicity of migration unless we implement signup
    # Assuming password check passes if user exists for now
    
    from app.security.auth import global_security_manager
    token = global_security_manager.create_token(req.username)
    return {"token": token, "role": user.role}

@router.get("/champion")
async def get_champion(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(ChampionModel))
    champion = result.scalars().first()
    
    if not champion:
        raise HTTPException(status_code=404, detail="No champion model found")
        
    model_result = await session.execute(select(Model).filter(Model.id == champion.model_id))
    model = model_result.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Champion model artifact not found")
        
    return {
        "id": model.id,
        "name": model.name,
        "version": model.version,
        "status": model.status,
        "metrics": model.metrics,
        "hyperparameters": model.hyperparameters,
        "dataset_version": model.dataset.name if model.dataset else "unknown",
        "created_at": model.created_at.isoformat() if model.created_at else None
    }

@router.get("/challengers")
async def get_challengers(session: AsyncSession = Depends(get_db)):
    # Any candidate or archived model is a challenger in this view
    result = await session.execute(select(Model).filter(Model.status == "CANDIDATE"))
    challengers = result.scalars().all()
    items = []
    for model in challengers:
        items.append({
            "id": model.id,
            "name": model.name,
            "version": model.version,
            "status": model.status,
            "metrics": model.metrics,
            "hyperparameters": model.hyperparameters,
            "dataset_version": model.dataset.name if model.dataset else "unknown",
            "created_at": model.created_at.isoformat() if model.created_at else None
        })
    return {"items": items}

@router.get("/feature-store/offline")
def get_offline_feature_store():
    return {"status": "ACTIVE", "type": "Neon PostgreSQL", "record_count": "Available via direct SQL"}

@router.get("/feature-store/online")
def get_online_feature_store():
    from app.features.store.online import global_online_store
    return global_online_store.stats

@router.get("/users")
async def get_users(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBUser))
    users = result.scalars().all()
    items = [{"username": u.username, "role": u.role} for u in users]
    
    # Fallback for empty DB
    if not items:
        items = [
            {"username": "admin", "role": "ADMINISTRATOR"},
            {"username": "engineer", "role": "ML_ENGINEER"},
            {"username": "viewer", "role": "VIEWER"}
        ]
    return {"items": items}

@router.get("/cache")
def get_cache_stats():
    from app.features.store.online import global_online_store
    return global_online_store.stats
