import hashlib
import secrets


def generate_api_key() -> tuple[str, str]:
    """Generates a raw API key and its hash for storage."""
    raw_key = f"ff_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def get_api_key_hash(raw_key: str) -> str:
    """Hashes a raw API key for database lookup."""
    return hashlib.sha256(raw_key.encode()).hexdigest()
