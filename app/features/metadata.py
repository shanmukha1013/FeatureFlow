"""
Immutable configuration schema for feature representations.

Strictly defines the metadata contract required for every feature, enabling
registry indexing, searchability, and safe transformation dependencies.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass(frozen=True)
class FeatureMetadata:
    """
    Immutable metadata encapsulating feature context and operational properties.

    Attributes:
        name: A unique string identifier for the feature.
        description: Semantic context explaining the feature's logic.
        version: Semantic version (e.g., '1.0.0') for managing feature drift.
        owner: The team or individual responsible for maintaining the feature.
        source_columns: Ordered list of raw column names required for computation.
        data_type: Expected pandas output dtype.
        tags: Optional categorical tags for registry organization.
        nullable: Whether the resulting feature tolerates null values.
        default_value: Explicit fallback value if nulls are prohibited.
    """
    feature_id: str
    name: str
    description: str
    version: str
    owner: str
    source_dataset: str
    source_columns: List[str]
    feature_type: str
    transformation: str
    data_type: str
    status: str = "ACTIVE"
    created_at: str = ""
    last_updated: str = ""
    tags: List[str] = field(default_factory=list)
    nullable: bool = True
    default_value: Optional[Any] = None

    def __post_init__(self) -> None:
        """Enforces structural integrity upon instantiation."""
        if not self.name.strip():
            raise ValueError("Feature metadata 'name' cannot be empty or whitespace.")
        if not self.version.strip():
            raise ValueError("Feature metadata 'version' cannot be empty.")
        if not self.source_columns:
            raise ValueError(f"Feature '{self.name}' must declare at least one source column.")
        if not isinstance(self.tags, list):
            raise TypeError(f"Tags for '{self.name}' must be a list of strings.")
