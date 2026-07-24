"""
Public interface for the Data Layer.

Aggregates classes and exceptions to provide a clean import boundary
for external consumers.
"""
from .exceptions import (
    DataLayerError,
    DataLoaderError,
    SchemaValidationError,
    DataValidationError,
    DataProfilingError,
    DataPreprocessingError,
)
from .schema import ColumnSchema, DatasetSchema, SchemaRegistry
from .loader import CSVDataLoader, DataLoaderProtocol
from .discovery import DatasetDiscovery
from .validator import DataValidator
from .profiler import DataProfiler, ProfilingReport
from .preprocessor import DataPreprocessor

__all__ = [
    "DataLayerError",
    "DataLoaderError",
    "SchemaValidationError",
    "DataValidationError",
    "DataProfilingError",
    "DataPreprocessingError",
    "ColumnSchema",
    "DatasetSchema",
    "SchemaRegistry",
    "DatasetDiscovery",
    "DataLoaderProtocol",
    "CSVDataLoader",
    "DataValidator",
    "DataProfiler",
    "ProfilingReport",
    "DataPreprocessor",
]
