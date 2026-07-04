"""
Defines the immutable prediction response contract.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, List

@dataclass(frozen=True)
class PredictionResponse:
    """
    Strict boundary object for outgoing inference results.
    """
    request_id: str
    prediction: Any
    model_id: str
    model_version: str
    latency_ms: float
    probability: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
