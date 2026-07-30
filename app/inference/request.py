"""
Defines the immutable prediction request contract.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class PredictionRequest:
    """
    Strict boundary object for incoming inference requests.
    """
    entity_id: str
    features: Dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    explain: bool = False
