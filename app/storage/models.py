"""
Storage domain models and metadata objects.

Provides strongly typed, immutable representations of storage entities and their 
operational state, completely separating persistence concerns from upstream logic.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime

@dataclass(frozen=True)
class StorageMetadata:
    """
    Comprehensive operational metadata for a persisted feature dataset.
    
    Attributes:
        dataset_name: The physical namespace or table name of the dataset.
        version: The semantic version or timestamp version of the data.
        created_at: UTC timestamp when this dataset version was persisted.
        row_count: The total number of feature records stored.
        feature_count: The total number of discrete features stored.
        schema_version: Identifier for the structural schema (e.g., hash or version).
        entity_id_column: The primary key column used for retrieval.
        integrity_hash: Optional checksum or hash ensuring data hasn't mutated.
    """
    dataset_name: str
    version: str
    created_at: datetime
    row_count: int
    feature_count: int
    schema_version: str = "1.0"
    entity_id_column: str = "entity_id"
    integrity_hash: Optional[str] = None

@dataclass(frozen=True)
class FeatureRecord:
    """
    A single feature vector record retrieved from the online store.
    
    Attributes:
        entity_id: The primary key of the entity (e.g., user_id).
        features: Dictionary mapping feature names to their computed values.
        timestamp: Optional UTC timestamp of when this vector was computed.
    """
    entity_id: Any
    features: Dict[str, Any]
    timestamp: Optional[datetime] = None
