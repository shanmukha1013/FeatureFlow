from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class DatasetMetadata:
    dataset_id: str
    dataset_name: str
    absolute_path: str
    relative_path: str
    file_size: int
    created_time: str
    modified_time: str
    extension: str
    status: str
    discovery_timestamp: str
    registration_timestamp: str
    source_type: str
    version: str
    checksum: str
    
    # Introspection Metadata
    row_count: int = 0
    column_count: int = 0
    column_names: List[str] = field(default_factory=list)
    inferred_dtypes: Dict[str, str] = field(default_factory=dict)
    estimated_memory_bytes: int = 0
    
    # Pipeline Status Metadata
    validation_status: str = "PENDING"
    profiling_status: str = "PENDING"
    schema_status: str = "PENDING"
    duplicate_count: int = 0
    null_percentage_max: float = 0.0
    last_profile_time: Optional[str] = None

class DatasetRegistry:
    def __init__(self):
        self._datasets: Dict[str, DatasetMetadata] = {}

    def register(self, metadata: DatasetMetadata) -> None:
        self._datasets[metadata.dataset_id] = metadata
        logger.info(f"Dataset successfully registered in DatasetRegistry: {metadata.dataset_name}")

    def get(self, dataset_id: str) -> DatasetMetadata:
        if dataset_id not in self._datasets:
            raise KeyError(f"Dataset '{dataset_id}' not found in registry.")
        return self._datasets[dataset_id]

    def list_datasets(self) -> List[DatasetMetadata]:
        return list(self._datasets.values())

global_dataset_registry = DatasetRegistry()
