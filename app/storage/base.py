"""
Abstract storage contracts for FeatureFlow.

Defines a strict, unified interface for all concrete storage implementations 
to ensure safe persistence, upsert semantics, and metadata consistency.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Any, List, Optional

class BaseFeatureStore(ABC):
    """
    Abstract contract for feature storage backends.
    """
    
    @abstractmethod
    def save(self, dataset_name: str, df: pd.DataFrame, version: str = "latest") -> None:
        """
        Persists a full feature dataset to the backend.
        Must safely overwrite or replace the dataset for the given version.
        """
        ...

    @abstractmethod
    def load(self, dataset_name: str, entity_ids: Optional[List[Any]] = None, version: str = "latest") -> pd.DataFrame:
        """
        Retrieves a feature dataset from the backend.
        Returns the entire dataset if entity_ids is None.
        """
        ...

    @abstractmethod
    def upsert(self, dataset_name: str, df: pd.DataFrame, version: str = "latest") -> None:
        """
        Updates an existing feature dataset enforcing true Upsert (Insert on Conflict Update) semantics.
        Must use the configured entity_id column as the primary constraint.
        """
        ...

    @abstractmethod
    def delete(self, dataset_name: str, version: str = "latest") -> None:
        """Removes a feature dataset entirely from the backend."""
        ...

    @abstractmethod
    def exists(self, dataset_name: str, version: str = "latest") -> bool:
        """Verifies if a feature dataset namespace exists in the backend."""
        ...
        
    @abstractmethod
    def list(self) -> List[str]:
        """Returns a list of all available feature dataset namespaces."""
        ...
