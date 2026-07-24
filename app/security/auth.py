import jwt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from typing import Optional
from fastapi import HTTPException, status

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt according to settings."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> bool:
    """Validates that password meets enterprise strength criteria."""
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    return True


def generate_api_key() -> tuple[str, str]:
    """Generates a raw API key and its hash for storage."""
    raw_key = f"ff_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def get_api_key_hash(raw_key: str) -> str:
    """Hashes a raw API key for database lookup."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_access_token(user_id: str, username: str, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a short-lived JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    # Use the first key for signing
    signing_key = settings.jwt_secret_keys.split(",")[0].strip()

    to_encode = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, signing_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(user_id: str, session_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a long-lived JWT refresh token bounded to a session."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    signing_key = settings.jwt_secret_keys.split(",")[0].strip()

    to_encode = {
        "sub": str(user_id),
        "jti": session_id,
        "type": "refresh",
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, signing_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decodes a JWT token, supporting key rotation by trying all keys.
    Raises HTTPException on failure.
    """
    keys = [k.strip() for k in settings.jwt_secret_keys.split(",") if k.strip()]

    for idx, key in enumerate(keys):
        try:
            payload = jwt.decode(token, key, algorithms=[settings.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            # If this is the last key, it's truly invalid
            if idx == len(keys) - 1:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            continue  # Try next key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
