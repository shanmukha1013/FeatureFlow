"""
Pydantic schemas for Management API responses.
"""
from pydantic import BaseModel
from typing import List

class PlatformOverviewSchema(BaseModel):
    platform_version: str
    health: str
    registered_models: int
    registered_features: int
    registered_datasets: int
    pipeline_count: int
    training_jobs: int
    serving_status: str
    monitoring_status: str
    inference_status: str

class SystemInfoSchema(BaseModel):
    python_version: str
    operating_system: str
    framework_version: str
    storage_backend: str
    monitoring_backend: str
    inference_backend: str
    training_backend: str
    
class StatisticsSchema(BaseModel):
    total_predictions: int
    average_latency: float
    training_count: int
    pipeline_count: int
    inference_count: int
    validation_failures: int

class AboutSchema(BaseModel):
    platform_name: str
    description: str
    version: str
    author: str
    license: str
    repository: str
    build_timestamp: str
    
class ConfigSchema(BaseModel):
    storage_backend: str
    monitoring_backend: str
    training_backend: str
    inference_backend: str
    serving_version: str
    enabled_modules: List[str]
