"""
Public interface for the Data Layer.

Aggregates classes and exceptions to provide a clean import boundary
for external consumers.
"""
from .discovery import DatasetDiscovery
from .exceptions import (
    DataLayerError,
    DataLoaderError,
    DataPreprocessingError,
    DataProfilingError,
    DataValidationError,
    SchemaValidationError,
)
from .loader import CSVDataLoader, DataLoaderProtocol
from .preprocessor import DataPreprocessor
from .profiler import DataProfiler, ProfilingReport
from .schema import ColumnSchema, DatasetSchema, SchemaRegistry
from .validator import DataValidator

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
