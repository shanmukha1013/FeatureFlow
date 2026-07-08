"""
RegistryModelLoader: Loads trained ML model artifacts from the local artifact store.

Acts as the bridge between the persisted artifact on disk and the in-memory
ModelPredictor at inference time.
"""
from app.inference.base import BaseModelLoader
from app.training.artifacts import LocalArtifactStore
from app.inference.exceptions import ModelLoadError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RegistryModelLoader(BaseModelLoader):
    """
    Loads serialized scikit-learn model artifacts from the LocalArtifactStore.
    """

    def __init__(self, artifact_store: LocalArtifactStore = None) -> None:
        self.artifact_store = artifact_store or LocalArtifactStore()

    def load(self, model_id: str, version: str):
        """
        Loads the model artifact for the given model_id and version string.

        Args:
            model_id: The unique model identifier (e.g. 'mdl_auctions_randomforest_v1').
            version:  The version tag (e.g. 'v1').

        Returns:
            The deserialized scikit-learn model object.

        Raises:
            ModelLoadError: If the artifact cannot be found or deserialized.
        """
        try:
            logger.info(f"Loading artifact for model_id={model_id}, version={version}")
            model = self.artifact_store.load(model_id, version)
            logger.info(f"Artifact loaded successfully: {model_id}")
            return model
        except FileNotFoundError as e:
            raise ModelLoadError(f"Artifact not found for model_id={model_id}, version={version}: {e}") from e
        except Exception as e:
            raise ModelLoadError(f"Failed to deserialize artifact for model_id={model_id}: {e}") from e
