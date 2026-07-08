"""
SecurityManager: Stateless token validation for FeatureFlow.

The security manager validates JWT tokens. User persistence is PostgreSQL.
The in-memory mock-user table has been completely removed.

Note: JWT is retained here only to maintain backward compatibility with the
existing management router's token validation middleware. No new JWT
features will be added (Phase 5 scope).
"""
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException

from app.security.models import User, Role, Permission, ROLE_PERMISSIONS
from app.utils.logger import get_logger

logger = get_logger(__name__)

SECRET_KEY = "enterprise-mlops-secret-key-do-not-use-in-prod"
ALGORITHM = "HS256"


class SecurityManager:
    """
    Provides stateless JWT token creation and validation.
    Does NOT maintain any in-memory user state - PostgreSQL is the user store.
    """

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_token(self, username: str, role: str = "VIEWER") -> str:
        """Creates a JWT token for the given username and role."""
        expires = datetime.utcnow() + timedelta(hours=8)
        payload = {
            "sub": username,
            "role": role,
            "exp": expires
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Token issued for user: {username}")
        return token

    def validate_token(self, token: str, required_permission: Optional[Permission] = None) -> dict:
        """
        Validates a JWT token.

        Returns:
            dict with 'username' and 'role' keys.

        Raises:
            HTTPException 401/403 on invalid or expired tokens.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            role_str = payload.get("role", "VIEWER")

            if not username:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            if required_permission:
                try:
                    role_enum = Role(role_str)
                    perms = ROLE_PERMISSIONS.get(role_enum, [])
                    if required_permission not in perms:
                        logger.warning(f"Permission denied for {username}: {required_permission}")
                        raise HTTPException(status_code=403, detail="Permission denied")
                except ValueError:
                    raise HTTPException(status_code=403, detail=f"Unknown role: {role_str}")

            return {"username": username, "role": role_str}

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")


global_security_manager = SecurityManager()
