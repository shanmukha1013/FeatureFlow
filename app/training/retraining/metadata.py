from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

class RetrainingTrigger(str, Enum):
    MANUAL = "MANUAL"
    SCHEDULE = "SCHEDULE"
    DATA_DRIFT = "DATA_DRIFT"
    MODEL_DRIFT = "MODEL_DRIFT"
    DATASET_UPDATED = "DATASET_UPDATED"
    FEATURE_CHANGED = "FEATURE_CHANGED"

class RetrainingStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass(frozen=True)
class RetrainingPolicy:
    policy_id: str
    dataset_name: str
    trigger_type: RetrainingTrigger
    threshold: Optional[float] = None # e.g., PSI threshold
    enabled: bool = True

@dataclass(frozen=True)
class RetrainingJob:
    job_id: str
    policy_id: str
    trigger_type: RetrainingTrigger
    dataset_name: str
    status: RetrainingStatus = RetrainingStatus.RUNNING
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    champion_promoted: bool = False
    new_champion_id: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "policy_id": self.policy_id,
            "trigger_type": self.trigger_type.value,
            "dataset_name": self.dataset_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "champion_promoted": self.champion_promoted,
            "new_champion_id": self.new_champion_id,
            "error_message": self.error_message
        }
