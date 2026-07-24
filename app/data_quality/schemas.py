from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class DataContractSchema(BaseModel):
    dataset_name: str
    owner: Optional[str] = None
    schema_definition: Dict[str, str] = Field(..., description="Map of column name to data type")
    business_rules: Optional[Dict[str, Any]] = None
    primary_keys: Optional[List[str]] = None


class DataContractResponse(DataContractSchema):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    status: str
    created_at: datetime


class ExpectationResultSchema(BaseModel):
    expectation_type: str
    severity: str
    success: bool
    kwargs: Optional[Dict[str, Any]] = None
    observed_value: Optional[str] = None
    exception_info: Optional[str] = None


class ValidationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suite_id: str
    dataset_version_id: str
    success: bool
    quality_score: float
    critical_count: int
    error_count: int
    warning_count: int
    info_count: int
    execution_time_ms: float
    created_at: datetime
    results: List[ExpectationResultSchema] = []


class HealthTrendPoint(BaseModel):
    dataset_version_id: str
    quality_score: float
    created_at: datetime
    success: bool


class DatasetHealthTrendsResponse(BaseModel):
    dataset_name: str
    trends: List[HealthTrendPoint]
    average_score: float
    reliability_percentage: float
