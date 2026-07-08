"""
Coordinates Storage operations across multiple backends.

Acts as the exclusive entry point for persisting and retrieving features,
enforcing strict storage validation and generating operational metadata.
"""
import pandas as pd
import hashlib
from typing import Any, List
from datetime import datetime

from app.storage.base import BaseFeatureStore
from app.storage.exceptions import StorageValidationError
from dataclasses import dataclass

@dataclass
class StorageMetadata:
    dataset_name: str
    version: str
    created_at: datetime
    row_count: int
    feature_count: int
    schema_version: str
    entity_id_column: str
    integrity_hash: str
from app.utils.logger import get_logger

logger = get_logger(__name__)

class StorageManager:
    """
    Unified Facade coordinating the Online and Offline stores.
    
    Ensures data consistency, validates storage requirements, and routes 
    requests securely, preventing upstream layers from interacting directly 
    with database infrastructure.
    """
    def __init__(self, offline_store: BaseFeatureStore, online_store: BaseFeatureStore, entity_id_column: str = "entity_id") -> None:
        """
        Args:
            offline_store: The configured backend for historical batch storage.
            online_store: The configured backend for real-time vector storage.
            entity_id_column: The designated primary key column for all stored features.
        """
        self.offline_store = offline_store
        self.online_store = online_store
        self.entity_id_column = entity_id_column

    def _validate_for_storage(self, df: pd.DataFrame, dataset_name: str) -> None:
        """
        Performs storage-specific integrity checks on the incoming dataset.
        This does NOT duplicate the semantic checks done by the Data Layer.
        """
        if df is None or df.empty:
            raise StorageValidationError(f"Cannot process storage request for '{dataset_name}': DataFrame is empty or None.")

        if self.entity_id_column not in df.columns:
            raise StorageValidationError(
                f"Dataset '{dataset_name}' is missing the strictly required primary key: '{self.entity_id_column}'"
            )

        # Check for duplicated feature columns (excluding entity_id)
        columns = df.columns.tolist()
        if len(columns) != len(set(columns)):
            duplicates = [col for col in set(columns) if columns.count(col) > 1]
            raise StorageValidationError(f"Dataset '{dataset_name}' contains duplicate column names: {duplicates}")

    def _generate_metadata(self, dataset_name: str, df: pd.DataFrame, version: str) -> StorageMetadata:
        """Constructs detailed operational metadata for the persisted dataset."""
        columns = list(df.columns)
        # Exclude the entity ID column when counting pure features
        feature_count = len(columns) - 1 if self.entity_id_column in columns else len(columns)
        
        # Simple structural integrity hash based on column names and shape
        shape_signature = f"{dataset_name}:{version}:{len(df)}:{'-'.join(sorted(columns))}"
        integrity_hash = hashlib.sha256(shape_signature.encode()).hexdigest()
        
        return StorageMetadata(
            dataset_name=dataset_name,
            version=version,
            created_at=datetime.utcnow(),
            row_count=len(df),
            feature_count=feature_count,
            schema_version="1.0",
            entity_id_column=self.entity_id_column,
            integrity_hash=integrity_hash
        )

    def save_features(self, dataset_name: str, df: pd.DataFrame, version: str = "latest", sync_online: bool = True) -> StorageMetadata:
        """
        Validates and persists a final feature dataset to configured storage backends.
        """
        logger.info(f"StorageManager: Received save request for dataset '{dataset_name}' (v:{version}).")
        
        # Enforce storage structural constraints before allowing I/O
        self._validate_for_storage(df, dataset_name)
        
        # Persist to historical offline store
        self.offline_store.save(dataset_name, df, version)
        
        # Optionally synchronize vectors into the fast online store
        if sync_online:
            try:
                self.online_store.save(dataset_name, df, version)
            except Exception as e:
                # Online failure shouldn't necessarily rollback offline persistence
                logger.error(f"StorageManager: Synchronization to online store failed for '{dataset_name}': {e}")
                
        metadata = self._generate_metadata(dataset_name, df, version)
        logger.info(f"StorageManager: Persisted dataset '{dataset_name}'. Operational Hash: {metadata.integrity_hash[:8]}")
        return metadata

    def get_historical_features(self, dataset_name: str, version: str = "latest") -> pd.DataFrame:
        """Retrieves bulk historical features strictly from the offline store."""
        logger.info(f"StorageManager: Routing historical retrieval for '{dataset_name}' (v:{version}).")
        return self.offline_store.load(dataset_name, version=version)

    def get_online_features(self, dataset_name: str, entity_ids: List[Any], version: str = "latest") -> pd.DataFrame:
        """Retrieves low-latency feature vectors strictly from the online store."""
        logger.info(f"StorageManager: Routing online retrieval for {len(entity_ids)} entities in '{dataset_name}' (v:{version}).")
        return self.online_store.load(dataset_name, entity_ids, version=version)

    def list_historical_datasets(self) -> List[str]:
        """Exposes the list of strictly offline historical datasets."""
        return self.offline_store.list()
