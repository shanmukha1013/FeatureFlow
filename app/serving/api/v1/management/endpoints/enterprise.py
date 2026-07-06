from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(tags=["enterprise"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/security/login")
def login(req: LoginRequest):
    from app.security.auth import global_security_manager
    user = global_security_manager.users.get(req.username)
    if not user or user.password_hash != global_security_manager.hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = global_security_manager.create_token(req.username)
    return {"token": token, "role": user.role.value}

@router.get("/champion")
def get_champion():
    from app.serving.dependencies import _training_registry
    from app.training.metadata import ModelLifecycleState
    champion = None
    for mid in _training_registry.list_models():
        meta = _training_registry.get(mid)
        if meta.lifecycle_state == ModelLifecycleState.CHAMPION:
            champion = meta
            break
    if not champion:
        raise HTTPException(status_code=404, detail="No champion model found")
    return champion.to_dict()

@router.get("/challengers")
def get_challengers():
    from app.serving.dependencies import _training_registry
    from app.training.metadata import ModelLifecycleState
    challengers = []
    for mid in _training_registry.list_models():
        meta = _training_registry.get(mid)
        if meta.lifecycle_state == ModelLifecycleState.CHALLENGER:
            challengers.append(meta.to_dict())
    return {"items": challengers}

@router.get("/feature-store/offline")
def get_offline_feature_store():
    # Return some mock metadata about the offline store since it's SQLite/Postgres
    return {"status": "ACTIVE", "type": "Postgres (Simulated)", "record_count": "Available via direct SQL"}

@router.get("/feature-store/online")
def get_online_feature_store():
    from app.features.store.online import global_online_store
    return global_online_store.stats

@router.get("/users")
def get_users():
    from app.security.auth import global_security_manager
    users = [{"username": u.username, "role": u.role.value} for u in global_security_manager.users.values()]
    return {"items": users}

@router.get("/cache")
def get_cache_stats():
    from app.features.store.online import global_online_store
    return global_online_store.stats
