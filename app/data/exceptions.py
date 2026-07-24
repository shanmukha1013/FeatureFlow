"""
Centralized exception hierarchy for the Data Layer.

Ensures that errors originating in the Data Layer are explicitly typed
and decoupled from built-in Python exceptions or other layers.
"""


class DataLayerError(Exception):
    """Base exception for all errors within the Data Layer."""


class DataLoaderError(DataLayerError):
    """Raised when the loader encounters I/O errors or missing files."""


class SchemaValidationError(DataLayerError):
    """Raised when the dataset structure strictly violates the expected schema."""


class DataValidationError(DataLayerError):
    """Raised when dataset content (e.g., duplicates, nulls) violates validation rules."""


class DataProfilingError(DataLayerError):
    """Raised when statistical profiling fails on a dataset."""


class DataPreprocessingError(DataLayerError):
    """Raised when generic data cleaning operations fail."""
