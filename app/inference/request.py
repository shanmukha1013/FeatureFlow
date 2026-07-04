"""
Defines the immutable prediction request contract.
"""
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
import uuid

@dataclass(frozen=True)
class PredictionRequest:
    """
    Strict boundary object for incoming inference requests.
    """
    entity_id: str
    features: Dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
