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
    explanation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes PredictionResponse into a JSON-compatible dictionary for caching."""
        return {
            "request_id": self.request_id,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "probability": self.probability,
            "latency_ms": self.latency_ms,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "algorithm": self.algorithm,
            "timestamp": self.timestamp,
            "warnings": self.warnings,
            "top_contributors": self.top_contributors,
            "positive_contributors": self.positive_contributors,
            "negative_contributors": self.negative_contributors,
            "raw_scores": self.raw_scores,
            "explanation": self.explanation
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], override_request_id: Optional[str] = None) -> "PredictionResponse":
        """Deserializes PredictionResponse from cached JSON payload."""
        return cls(
            request_id=override_request_id or data.get("request_id", ""),
            prediction=data.get("prediction"),
            confidence=data.get("confidence"),
            probability=data.get("probability"),
            latency_ms=data.get("latency_ms", 0.0),
            model_name=data.get("model_name", ""),
            model_version=data.get("model_version", ""),
            algorithm=data.get("algorithm", ""),
            timestamp=data.get("timestamp", ""),
            warnings=data.get("warnings", []),
            top_contributors=data.get("top_contributors", []),
            positive_contributors=data.get("positive_contributors", []),
            negative_contributors=data.get("negative_contributors", []),
            raw_scores=data.get("raw_scores", {}),
            explanation=data.get("explanation")
        )
