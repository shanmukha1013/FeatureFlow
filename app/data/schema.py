"""
Provides schema definitions for dataset structures.

Ensures that incoming datasets adhere to strict contracts regarding 
required columns and data types before downstream processing.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass(frozen=True)
class ColumnSchema:
    """
    Immutable definition of a single dataset column.
    """
    name: str
    dtype: str
    required: bool = True
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Column name cannot be empty or whitespace.")
        if not self.dtype.strip():
            raise ValueError("Column dtype cannot be empty or whitespace.")

@dataclass(frozen=True)
class DatasetSchema:
    """
    Immutable definition of an expected dataset structure.
    """
    name: str
    columns: List[ColumnSchema]
    version: str = "1.0.0"
    entity_id_column: str = "entity_id"
    
    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Dataset schema name cannot be empty.")
        if not self.columns:
            raise ValueError(f"Dataset schema '{self.name}' must define at least one column.")
        if not self.version.strip():
            raise ValueError("Schema version cannot be empty.")
        if not self.entity_id_column.strip():
            raise ValueError("entity_id_column cannot be empty.")

    @property
    def required_columns(self) -> List[str]:
        return [col.name for col in self.columns if col.required]

    @property
    def expected_dtypes(self) -> Dict[str, str]:
        return {col.name: col.dtype for col in self.columns}


class SchemaRegistry:
    """
    Centralized registry for dataset schemas.
    Allows dynamic registration and discovery of datasets without hardcoding.
    """
    def __init__(self) -> None:
        self._schemas: Dict[str, DatasetSchema] = {}

    def register(self, schema: DatasetSchema) -> None:
        """Registers a schema by its name."""
        if schema.name in self._schemas:
            logger.warning(f"Overwriting existing schema registration for '{schema.name}'")
        self._schemas[schema.name] = schema
        logger.info(f"Registered schema: {schema.name} (v{schema.version})")

    def get(self, schema_name: str) -> DatasetSchema:
        """Retrieves a schema by name."""
        if schema_name not in self._schemas:
            raise KeyError(f"Schema '{schema_name}' is not registered.")
        return self._schemas[schema_name]

    def has_schema(self, schema_name: str) -> bool:
        """Checks if a schema exists."""
        return schema_name in self._schemas

    def list_schemas(self) -> List[str]:
        """Lists all registered schema names."""
        return list(self._schemas.keys())
