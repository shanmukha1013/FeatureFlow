"""
Defines the core feature abstraction contract.

Forces all analytical logic to adhere to a strict object-oriented interface,
guaranteeing self-validation and execution safety during transformation.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import List

from app.features.metadata import FeatureMetadata
from app.features.exceptions import InvalidFeatureError, FeatureTransformationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseFeature(ABC):
    """
    The abstract contract every FeatureFlow feature must fulfill.

    Subclasses must implement `transform()` to execute their business logic.
    """

    def __init__(self, metadata: FeatureMetadata):
        """
        Args:
            metadata: Strongly typed FeatureMetadata instance.
        """
        self._metadata = metadata
        self._validate_self()

    @property
    def metadata(self) -> FeatureMetadata:
        """Returns the immutable metadata associated with this feature."""
        return self._metadata

    @property
    def name(self) -> str:
        """Conveniently returns the strictly defined feature name."""
        return self._metadata.name

    def _validate_self(self) -> None:
        """
        Asserts the feature's fundamental structural integrity.
        Subclasses may override this to enforce custom instantiation invariants.
        """
        if not isinstance(self._metadata, FeatureMetadata):
            raise InvalidFeatureError(
                f"Feature '{getattr(self._metadata, 'name', 'Unknown')}' initialization failed: "
                "metadata must strictly be an instance of FeatureMetadata."
            )

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.Series:
        """
        Business logic for computing the feature.

        Args:
            df: Validated DataFrame guaranteed to contain the source_columns.

        Returns:
            A Pandas Series corresponding precisely to the input row dimensions.
        """
        ...

    def __call__(self, df: pd.DataFrame) -> pd.Series:
        """
        Executes the feature transformation safely via a standard lifecycle hook.

        Args:
            df: The raw input DataFrame.

        Returns:
            The computed feature Series.

        Raises:
            FeatureTransformationError: For missing columns or computation errors.
        """
        try:
            logger.debug(f"Applying feature logic: {self.name} (v{self.metadata.version})")

            # Defensive check: ensure the caller provided the required source context
            missing_cols: List[str] = [
                col for col in self.metadata.source_columns if col not in df.columns
            ]
            if missing_cols:
                raise FeatureTransformationError(
                    f"Execution aborted for '{self.name}': Missing required source columns -> {missing_cols}"
                )

            return self.transform(df)

        except FeatureTransformationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected failure while executing feature '{self.name}': {e}"
            logger.error(error_msg)
            raise FeatureTransformationError(error_msg) from e
