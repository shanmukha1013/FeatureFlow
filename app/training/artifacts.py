"""
Persists trained model binaries to the filesystem.
"""
import os
import hashlib
from typing import Any, Tuple, Optional

from app.training.exceptions import ArtifactError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class LocalArtifactStore:
    """
    Saves and retrieves trained model binaries locally using Joblib.
    Enforces artifact integrity via cryptographic checksums.
    """
    def __init__(self, base_dir: str = "models") -> None:
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        
    def _build_path(self, model_id: str, version: str) -> str:
        v_clean = str(version)[1:] if str(version).startswith('v') or str(version).startswith('V') else str(version)
        return os.path.join(self.base_dir, f"{model_id}_v{v_clean}.joblib")

    def _compute_checksum(self, file_path: str) -> str:
        """Generates a SHA-256 checksum for the specified file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256.update(byte_block)
        return sha256.hexdigest()

    def save(self, model: Any, model_id: str, version: str) -> Tuple[str, str]:
        """
        Serializes the model and returns the file path alongside its SHA-256 checksum.
        """
        logger.info(f"Persisting artifact '{model_id}' (v{version}) to '{self.base_dir}'.")
        try:
            import joblib
            file_path = self._build_path(model_id, version)
            joblib.dump(model, file_path)
            
            checksum = self._compute_checksum(file_path)
            logger.info(f"Artifact persisted successfully. Integrity checksum: {checksum[:8]}...")
            
            return file_path, checksum
        except Exception as e:
            raise ArtifactError(f"Failed to serialize model artifact '{model_id}': {e}") from e

    def load(self, model_id: str, version: str, expected_checksum: Optional[str] = None) -> Any:
        """
        Deserializes a model, optionally validating its cryptographic integrity.
        """
        file_path = self._build_path(model_id, version)
        if not os.path.exists(file_path):
            raise ArtifactError(f"Artifact not found at path: {file_path}")
            
        if expected_checksum:
            actual_checksum = self._compute_checksum(file_path)
            if actual_checksum != expected_checksum:
                logger.error(f"Integrity failure for artifact '{model_id}'. Expected {expected_checksum}, got {actual_checksum}.")
                raise ArtifactError("Artifact checksum verification failed. The file may be corrupted or tampered with.")
            
        try:
            import joblib
            return joblib.load(file_path)
        except Exception as e:
            raise ArtifactError(f"Failed to deserialize model artifact at '{file_path}': {e}") from e

    def delete(self, model_id: str, version: str) -> None:
        file_path = self._build_path(model_id, version)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted artifact at '{file_path}'.")

    def exists(self, model_id: str, version: str) -> bool:
        return os.path.exists(self._build_path(model_id, version))
