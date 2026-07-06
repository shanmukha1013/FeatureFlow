import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException
from app.security.models import User, Role, Permission, ROLE_PERMISSIONS
from app.monitoring.audit import AuditLogger, AuditEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)

SECRET_KEY = "enterprise-mlops-secret-key-do-not-use-in-prod"
ALGORITHM = "HS256"

class SecurityManager:
    def __init__(self):
        # Mock DB for users
        self.users = {
            "admin": User("u1", "admin", self.hash_password("admin"), Role.ADMINISTRATOR),
            "engineer": User("u2", "engineer", self.hash_password("engineer"), Role.ML_ENGINEER),
            "viewer": User("u3", "viewer", self.hash_password("viewer"), Role.VIEWER),
        }

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_token(self, username: str) -> str:
        user = self.users.get(username)
        if not user:
            raise ValueError("User not found")
            
        expires = datetime.utcnow() + timedelta(hours=8)
        payload = {
            "sub": user.username,
            "role": user.role.value,
            "exp": expires
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        AuditLogger.record(AuditEvent(event_name="SECURITY_LOGIN", component="SecurityManager", severity="INFO", payload={"username": username}))
        return token

    def validate_token(self, token: str, required_permission: Optional[Permission] = None) -> User:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            role_str = payload.get("role")
            
            if username not in self.users:
                raise HTTPException(status_code=401, detail="User not found")
                
            user = self.users[username]
            
            if required_permission:
                perms = ROLE_PERMISSIONS[user.role]
                if required_permission not in perms:
                    AuditLogger.record(AuditEvent(event_name="PERMISSION_DENIED", component="SecurityManager", severity="WARNING", payload={"username": username, "requested": required_permission.value}))
                    raise HTTPException(status_code=403, detail="Permission denied")
                    
            return user
            
        except jwt.ExpiredSignatureError:
            AuditLogger.record(AuditEvent(event_name="TOKEN_EXPIRED", component="SecurityManager", severity="WARNING", payload={}))
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

global_security_manager = SecurityManager()
