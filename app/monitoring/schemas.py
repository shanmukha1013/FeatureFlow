from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class MonitoringRunRequest(BaseModel):
    reference_dataset_id: str
    current_dataset_id: str


class MonitoringReportResponse(BaseModel):
    id: str
    reference_dataset_id: Optional[str]
    current_dataset_id: Optional[str]
    drift_detected: bool
    metrics: Optional[Dict[str, Any]]
    status: str
    html_path: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
