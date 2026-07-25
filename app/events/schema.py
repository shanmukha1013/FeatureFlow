from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


class EventType(str, Enum):
    # Data Events
    DATASET_UPLOADED = "Dataset.Uploaded"
    DATASET_VALIDATED = "Dataset.Validated"
    DATASET_FAILED = "Dataset.Failed"

    # Feature Events
    DATASET_PROFILED = "Dataset.Profiled"
    FEATURES_REGISTERED = "Features.Registered"
    FEATURE_MATERIALIZED = "Feature.Materialized"
    FEATURE_DRIFT_DETECTED = "Feature.DriftDetected"
    FEATURE_RETRIEVED = "Feature.Retrieved"
    TRAINING_SERVING_SKEW_DETECTED = "Feature.TrainingServingSkewDetected"

    # ML Events
    JOB_STARTED = "Job.Started"
    JOB_COMPLETED = "Job.Completed"
    JOB_FAILED = "Job.Failed"
    MODEL_REGISTERED = "Model.Registered"
    MODEL_PROMOTED = "Model.Promoted"
    MODEL_ROLLED_BACK = "Model.RolledBack"

    # Inference Events
    INFERENCE_REQUESTED = "Inference.Requested"
    INFERENCE_COMPLETED = "Inference.Completed"
    INFERENCE_FAILED = "Inference.Failed"

    # Monitoring Events
    LATENCY_SPIKE = "Monitoring.LatencySpike"
    SYSTEM_HEALTH_CHANGE = "Monitoring.HealthChange"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    severity: EventSeverity = EventSeverity.INFO
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
