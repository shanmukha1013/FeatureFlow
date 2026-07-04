"""
Public API boundary for the Storage Layer.
"""
from .exceptions import (
    StorageError,
    StorageConnectionError,
    OfflineStorageError,
    OnlineStorageError,
    FeatureStorageError,
    FeatureNotFoundError,
)
from .models import StorageMetadata, FeatureRecord
from .base import BaseFeatureStore
from .offline_store import PostgresOfflineStore
from .online_store import RedisOnlineStore
from .manager import StorageManager

__all__ = [
    "StorageError",
    "StorageConnectionError",
    "OfflineStorageError",
    "OnlineStorageError",
    "FeatureStorageError",
    "FeatureNotFoundError",
    "StorageMetadata",
    "FeatureRecord",
    "BaseFeatureStore",
    "PostgresOfflineStore",
    "RedisOnlineStore",
    "StorageManager",
]
