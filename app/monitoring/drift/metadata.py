from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum

class DriftSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    NONE = "NONE"

@dataclass(frozen=True)
class DriftAlert:
    feature: str
    severity: DriftSeverity
    drift_score: float
    metric: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class DriftReport:
    model_id: str
    timestamp: datetime
    overall_drift_score: float
    severity: DriftSeverity
    drifted_features: List[Dict[str, Any]]
    recommendations: List[str]
    model_drift: Dict[str, Any] = field(default_factory=dict)
