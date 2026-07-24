"""
Defines models for tracking the execution state and results of pipelines.

Ensures that execution telemetry (success, failures, validation reports,
and storage metadata) is strongly typed and preserved for upstream audits.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from app.data.validator import ValidationReport
from app.data.profiler import ProfilingReport


@dataclass
class DatasetExecutionReport:
    """Tracks the execution results for a single dataset within a pipeline."""
    dataset_name: str
    status: str = "PENDING"  # Valid states: PENDING, SUCCESS, FAILED
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    validation_report: Optional[ValidationReport] = None
    profiling_report: Optional[ProfilingReport] = None
    feature_count: int = 0
    storage_metadata: Optional[Any] = None  # Holds a Dataset ORM record when available
    error_message: Optional[str] = None

    def mark_success(self) -> None:
        self.status = "SUCCESS"
        self.end_time = datetime.now(timezone.utc)

    def mark_failure(self, error: str) -> None:
        self.status = "FAILED"
        self.error_message = error
        self.end_time = datetime.now(timezone.utc)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0


@dataclass
class PipelineExecutionReport:
    """Aggregates execution reports across a full end-to-end pipeline run."""
    pipeline_name: str
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    dataset_reports: Dict[str, DatasetExecutionReport] = field(default_factory=dict)

    def mark_complete(self) -> None:
        self.end_time = datetime.now(timezone.utc)

    @property
    def total_duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0

    @property
    def is_successful(self) -> bool:
        if not self.dataset_reports:
            return False
        return all(r.status == "SUCCESS" for r in self.dataset_reports.values())
