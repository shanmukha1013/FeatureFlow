"""
Centralized exception hierarchy for the Storage Layer.

Isolates infrastructure and persistence errors from business logic, ensuring 
that failures in databases or caches are explicitly typed and safely handled.
"""

class StorageError(Exception):
    """Base exception for all Storage Layer errors."""
    pass

class StorageConnectionError(StorageError):
    """Raised when the platform fails to connect to an underlying storage backend."""
    pass

class StorageValidationError(StorageError):
    """Raised when a feature dataset fails storage-level structural integrity checks."""
    pass

class OfflineStorageError(StorageError):
    """Raised during operations specific to the Offline Feature Store (e.g., PostgreSQL)."""
    pass

class OnlineStorageError(StorageError):
    """Raised during operations specific to the Online Feature Store (e.g., Redis)."""
    pass

class FeatureStorageError(StorageError):
    """Raised when attempting to store or retrieve malformed or missing features."""
    pass

class FeatureNotFoundError(StorageError):
    """Raised when a specifically requested feature or dataset cannot be found in storage."""
    pass
