"""
Defines the immutable prediction response contract.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict

@dataclass(frozen=True)
class PredictionResponse:
    """
    Strict boundary object for outgoing inference results.
    """
    request_id: str
    prediction: Any
    confidence: Optional[float]
    probability: Optional[float]
    latency_ms: float
    model_name: str
    model_version: str
    algorithm: str
    timestamp: str
    warnings: List[str] = field(default_factory=list)
    top_contributors: List[Dict[str, Any]] = field(default_factory=list)
    positive_contributors: List[Dict[str, Any]] = field(default_factory=list)
    negative_contributors: List[Dict[str, Any]] = field(default_factory=list)
    raw_scores: Dict[str, float] = field(default_factory=dict)
