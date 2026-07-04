"""
Defines immutable metadata contracts and reporting structures for trained models.

Ensures absolute reproducibility by tracking the exact lineage of algorithms, 
hyperparameters, features, and evaluation metrics tied to every trained artifact.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

class ModelLifecycleState(str, Enum):
    """Represents the operational status of a trained model."""
    EXPERIMENTAL = "EXPERIMENTAL"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"

@dataclass(frozen=True)
class ModelMetadata:
    """
    Immutable record of a successful model training lifecycle.
    """
    model_id: str
    model_version: str
    algorithm: str
    target_column: str
    feature_version: str
    dataset_version: str
    hyperparameters: Dict[str, Any]
    metrics: Dict[str, Any]
    artifact_path: str
    artifact_checksum: str
    dataset_size: int
    feature_count: int
    feature_names: List[str]  # Added to fix Inference Layer integration bug
    split_config: Dict[str, Any]
    training_duration_ms: float
    lifecycle_state: ModelLifecycleState = ModelLifecycleState.EXPERIMENTAL
    created_by: str = "platform"
    training_timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the metadata for registry storage."""
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "algorithm": self.algorithm,
            "target_column": self.target_column,
            "feature_version": self.feature_version,
            "dataset_version": self.dataset_version,
            "hyperparameters": self.hyperparameters,
            "metrics": self.metrics,
            "artifact_path": self.artifact_path,
            "artifact_checksum": self.artifact_checksum,
            "dataset_size": self.dataset_size,
            "feature_count": self.feature_count,
            "feature_names": self.feature_names,
            "split_config": self.split_config,
            "training_duration_ms": self.training_duration_ms,
            "lifecycle_state": self.lifecycle_state.value,
            "created_by": self.created_by,
            "training_timestamp": self.training_timestamp.isoformat()
        }

@dataclass
class TrainingReport:
    """
    Structured report tracking the end-to-end training execution pipeline.
    """
    model_id: str
    status: str = "PENDING"
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    metadata: Optional[ModelMetadata] = None
    error_message: Optional[str] = None
    
    def mark_success(self, metadata: ModelMetadata) -> None:
        self.status = "SUCCESS"
        self.metadata = metadata
        self.end_time = datetime.utcnow()
        
    def mark_failure(self, error: str) -> None:
        self.status = "FAILED"
        self.error_message = error
        self.end_time = datetime.utcnow()
        
    @property
    def total_duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0
