"""
Centralized exception hierarchy for the Storage Layer.

Isolates infrastructure and persistence errors from business logic, ensuring
that failures in databases or caches are explicitly typed and safely handled.
"""


class StorageError(Exception):
    """Base exception for all Storage Layer errors."""


class StorageConnectionError(StorageError):
    """Raised when the platform fails to connect to an underlying storage backend."""


class StorageValidationError(StorageError):
    """Raised when a feature dataset fails storage-level structural integrity checks."""


class OfflineStorageError(StorageError):
    """Raised during operations specific to the Offline Feature Store (e.g., PostgreSQL)."""


class OnlineStorageError(StorageError):
    """Raised during operations specific to the Online Feature Store (e.g., Redis)."""


class FeatureStorageError(StorageError):
    """Raised when attempting to store or retrieve malformed or missing features."""


class FeatureNotFoundError(StorageError):
    """Raised when a specifically requested feature or dataset cannot be found in storage."""
