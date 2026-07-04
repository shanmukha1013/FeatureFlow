"""
Maintains inference-specific model selection and logical routing.
"""
from typing import Dict, Tuple

from app.inference.exceptions import InferenceError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class InferenceModelRegistry:
    """
    Maps logical aliases (e.g. 'production', 'shadow', 'champion') to 
    physical model IDs and versions. This decouples the API layer from 
    hardcoding specific trained artifact IDs and enables safe rollouts.
    """
    def __init__(self) -> None:
        # Dictionary mapping alias -> (model_id, version)
        self._aliases: Dict[str, Tuple[str, str]] = {}
        self._default_alias: str = "default"

    def set_alias(self, alias: str, model_id: str, version: str) -> None:
        """Binds a logical alias securely to a concrete model artifact."""
        if not alias or not str(alias).strip():
            raise InferenceError("Routing alias cannot be empty or null.")
        if not model_id or not version:
            raise InferenceError("Target model_id and version cannot be empty.")
            
        self._aliases[alias] = (model_id, version)
        logger.info(f"Inference alias '{alias}' safely bound to model '{model_id}' (v{version}).")

    def set_default(self, model_id: str, version: str) -> None:
        """Sets the fallback default model."""
        self.set_alias(self._default_alias, model_id, version)

    def resolve(self, alias: str = None) -> Tuple[str, str]:
        """
        Resolves an alias to its concrete model_id and version.
        Falls back to the default alias if none provided.
        """
        target = alias or self._default_alias
        if target not in self._aliases:
            raise InferenceError(f"Cannot resolve inference routing: No active model bound to alias '{target}'.")
        return self._aliases[target]
        
    def list_aliases(self) -> Dict[str, Tuple[str, str]]:
        """Returns a snapshot of the current operational routing table."""
        return self._aliases.copy()
