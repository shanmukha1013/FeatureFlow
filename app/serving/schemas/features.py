"""
Pydantic contracts for Online Feature Store endpoints.
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Union


class StoreFeatureRequestSchema(BaseModel):
    dataset: str
    entity_id: str
    feature_values: Dict[str, Any]
    feature_version: Union[int, str] = 1
    dataset_version: Union[str, int] = 1
    ttl: Optional[int] = None


class StoreFeatureBatchRequestSchema(BaseModel):
    dataset: str
    entity_features_map: Dict[str, Dict[str, Any]]
    feature_version: Union[int, str] = 1
    dataset_version: Union[str, int] = 1
    ttl: Optional[int] = None


class RefreshFeatureRequestSchema(BaseModel):
    dataset: str
    entity_id: str
    ttl: Optional[int] = None


class FeatureVectorResponseSchema(BaseModel):
    values: Dict[str, Any]
    names: List[str]
    version: Union[int, str]
    timestamp: str
    dataset_version: Union[str, int]
