"""
InferenceModelRegistry: A lightweight in-memory registry that tracks which
model versions are currently loaded and ready for inference.

This is NOT a metadata store - that is PostgreSQL.
This is purely the in-memory index of model_id -> predictor for fast routing.
"""
from typing import Dict, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InferenceModelRegistry:
    """
    Maintains an in-memory map of model IDs to their loaded predictors.
    Populated at startup by loading champions from PostgreSQL.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, object] = {}
        self._default_model_id: Optional[str] = None

    def register(self, model_id: str, predictor: object, is_default: bool = False) -> None:
        """Register a loaded predictor under a given model_id."""
        self._registry[model_id] = predictor
        if is_default or not self._default_model_id:
            self._default_model_id = model_id
        logger.info(f"Registered predictor for model_id={model_id}, is_default={is_default}")

    def get(self, model_id: str) -> Optional[object]:
        """Retrieve a predictor by model_id."""
        return self._registry.get(model_id)

    def get_default(self) -> Optional[object]:
        """Returns the default/champion predictor."""
        if self._default_model_id:
            return self._registry.get(self._default_model_id)
        return None

    def list_model_ids(self):
        """Returns all registered model IDs."""
        return list(self._registry.keys())

    def clear(self) -> None:
        """Clears all registered predictors."""
        self._registry.clear()
        self._default_model_id = None

    @property
    def default_model_id(self) -> Optional[str]:
        return self._default_model_id

    def __len__(self) -> int:
        return len(self._registry)
