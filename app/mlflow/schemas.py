from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MLflowTrainRequest(BaseModel):
    dataset_id: str
    algorithm: str
    hyperparameters: Optional[Dict[str, Any]] = {}
    target_column: Optional[str] = "target"


class MLflowTrainResponse(BaseModel):
    run_id: str
    experiment_id: str
    status: str
    metrics: Optional[Dict[str, float]]
    parameters: Optional[Dict[str, Any]]


class MLflowPromoteRequest(BaseModel):
    model_name: str
    version: str
    alias: str


class MLflowPromoteResponse(BaseModel):
    model_name: str
    version: str
    alias: str
    status: str


class MLflowRunResponse(BaseModel):
    run_id: str
    experiment_id: str
    status: str
    metrics: Dict[str, float]
    params: Dict[str, str]


class ModelAliases(BaseModel):
    development: Optional[str] = None
    staging: Optional[str] = None
    production: Optional[str] = None
    champion: Optional[str] = None
    challenger: Optional[str] = None
    archived: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class MLflowModelResponse(BaseModel):
    name: str
    aliases: ModelAliases = Field(default_factory=ModelAliases)
    latest_versions: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)
