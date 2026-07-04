"""
Maintains the centralized Model Registry.

Tracks the exact provenance, lifecycle state, and artifacts for every 
trained machine learning model.
"""
import json
import os
from typing import Dict, List
from threading import Lock

from app.training.metadata import ModelMetadata, ModelLifecycleState
from app.training.exceptions import RegistryError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class LocalModelRegistry:
    """
    Persists and retrieves immutable ModelMetadata objects locally.
    Future-ready to be swapped with a remote MLflow or similar registry.
    """
    def __init__(self, base_dir: str = "models") -> None:
        self.registry_file = os.path.abspath(os.path.join(base_dir, "registry.json"))
        self._lock = Lock()
        self._models: Dict[str, ModelMetadata] = {}
        
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.registry_file):
            return
            
        try:
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
                for model_id, raw_meta in data.items():
                    from datetime import datetime
                    if "training_timestamp" in raw_meta and isinstance(raw_meta["training_timestamp"], str):
                        raw_meta["training_timestamp"] = datetime.fromisoformat(raw_meta["training_timestamp"])
                        
                    # Handle enum mapping safely for backwards compatibility
                    if "lifecycle_state" in raw_meta:
                        raw_meta["lifecycle_state"] = ModelLifecycleState(raw_meta["lifecycle_state"])
                        
                    self._models[model_id] = ModelMetadata(**raw_meta)
            logger.info(f"Loaded {len(self._models)} models from local registry.")
        except Exception as e:
            raise RegistryError(f"Failed to load registry from '{self.registry_file}': {e}") from e

    def _save(self) -> None:
        try:
            with open(self.registry_file, 'w') as f:
                data = {m_id: meta.to_dict() for m_id, meta in self._models.items()}
                json.dump(data, f, indent=4)
        except Exception as e:
            raise RegistryError(f"Failed to save registry to '{self.registry_file}': {e}") from e

    def register(self, metadata: ModelMetadata) -> None:
        """
        Registers a new model into the system.
        """
        logger.info(f"Registering model '{metadata.model_id}' (v{metadata.model_version}).")
        
        with self._lock:
            if metadata.model_id in self._models:
                logger.warning(f"Overwriting existing registry entry for model '{metadata.model_id}'.")
                
            self._models[metadata.model_id] = metadata
            self._save()
            
        logger.info("Model registered successfully.")

    def update_lifecycle_state(self, model_id: str, new_state: ModelLifecycleState) -> None:
        """
        Transitions a registered model to a new operational state (e.g. EXPERIMENTAL -> ACTIVE).
        """
        logger.info(f"Transitioning model '{model_id}' state to {new_state.value}.")
        with self._lock:
            if model_id not in self._models:
                raise RegistryError(f"Cannot update state: Model '{model_id}' is not registered.")
                
            # ModelMetadata is frozen, so we must recreate it to mutate the state
            old_meta = self._models[model_id]
            meta_dict = old_meta.to_dict()
            meta_dict["lifecycle_state"] = new_state
            
            from datetime import datetime
            meta_dict["training_timestamp"] = datetime.fromisoformat(meta_dict["training_timestamp"])
            
            self._models[model_id] = ModelMetadata(**meta_dict)
            self._save()

    def get(self, model_id: str) -> ModelMetadata:
        """Retrieves model metadata by ID."""
        with self._lock:
            if model_id not in self._models:
                raise RegistryError(f"Model '{model_id}' is not registered.")
            return self._models[model_id]

    def list_models(self) -> List[str]:
        """Returns a list of all registered model IDs."""
        with self._lock:
            return list(self._models.keys())
