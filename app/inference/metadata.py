"""
Immutable models for tracking inference telemetry.

Provides complete observability and auditability for every prediction
served by the platform.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class InferenceMetadata:
    """
    Immutable record of a prediction execution for operational auditability.
    """
    request_id: str
    model_id: str
    model_version: str
    model_alias: str
    feature_version: str
    dataset_version: str
    artifact_checksum: str
    latency_ms: float
    prediction_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
