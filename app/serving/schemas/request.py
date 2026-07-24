"""
Pydantic contracts for incoming API requests.
Isolates API payload validation from internal domain models.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class PredictRequestSchema(BaseModel):
    """
    Schema for executing a prediction.
    """
    entity_id: str = Field(..., description="Unique identifier for the prediction target.")
    features: Dict[str, Any] = Field(..., description="Feature vector for inference.")
    alias: Optional[str] = Field("default", description="Logical model alias to route the request.")
    explain: bool = Field(False, description="Generate a SHAP explanation for this prediction in the background.")
