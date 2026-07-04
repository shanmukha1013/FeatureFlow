"""
Retrieves serialized models for inference.
"""
from typing import Any

from app.inference.base import BaseModelLoader
from app.inference.exceptions import ModelLoadError
from app.training.artifacts import LocalArtifactStore
from app.training.registry import LocalModelRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RegistryModelLoader(BaseModelLoader):
    """
    Safely loads a model binary explicitly bound to its metadata in the Training Registry.
    Validates cryptographic checksums if available to prevent corrupted inference.
    """
    def __init__(self, registry: LocalModelRegistry, artifact_store: LocalArtifactStore) -> None:
        self.registry = registry
        self.artifact_store = artifact_store

    def load(self, model_id: str, version: str) -> Any:
        logger.info(f"Initiating load sequence for model '{model_id}' (v{version}).")
        try:
            # 1. Fetch authoritative metadata
            metadata = self.registry.get(model_id)
            
            if metadata.model_version != version:
                raise ModelLoadError(
                    f"Version mismatch. Requested v{version}, but registry head for '{model_id}' is v{metadata.model_version}."
                )
                
            # 2. Load the binary, strictly verifying its checksum against the metadata
            model = self.artifact_store.load(
                model_id=model_id, 
                version=version, 
                expected_checksum=metadata.artifact_checksum
            )
            
            logger.info(f"Successfully loaded and verified model '{model_id}'.")
            return model
            
        except Exception as e:
            error_msg = f"Failed to safely load model '{model_id}' (v{version}): {e}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from e
