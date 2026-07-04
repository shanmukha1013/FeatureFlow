"""
Executes feature computation workflows.

Given a feature registry and a sequence of requested feature names, the Transformer 
iterates through the features, executes their safe call chains, and bundles the 
resulting vectors into a finalized, decoupled dataset.
"""
import time
import pandas as pd
from typing import List, Dict

from app.features.registry import FeatureRegistry
from app.features.exceptions import FeatureTransformationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FeatureTransformer:
    """
    Coordinates the execution of multiple feature transformations over raw datasets.
    Provides detailed transformation auditing via structured logging.
    """
    def __init__(self, registry: FeatureRegistry) -> None:
        """
        Args:
            registry: A configured FeatureRegistry containing the definitions 
                      to execute.
        """
        self.registry = registry

    def transform(self, df: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
        """
        Computes the requested features using the provided DataFrame.
        
        Args:
            df: Validated, cleaned Pandas DataFrame acting as the root context.
            feature_names: Ordered list of feature names to extract from the registry.
            
        Returns:
            A new Pandas DataFrame containing *only* the computed feature columns.
            
        Raises:
            FeatureTransformationError: If any feature fails its computation lifecycle.
        """
        if df is None or df.empty:
            raise FeatureTransformationError("Transformer requires a populated DataFrame context.")
            
        if not feature_names:
            logger.warning("Transformation requested with an empty feature list. Returning empty DataFrame.")
            return pd.DataFrame()

        start_time = time.perf_counter()
        logger.info(f"Initiating transformation sequence for {len(feature_names)} features.")
        
        transformed_data: Dict[str, pd.Series] = {}
        
        for name in feature_names:
            feature = self.registry.get(name)
            try:
                feature_start = time.perf_counter()
                
                # The BaseFeature.__call__ handles validation and logging transparently
                series: pd.Series = feature(df)
                
                # Enforce identical naming convention to the metadata definition
                series.name = feature.name
                transformed_data[feature.name] = series
                
                feature_duration = (time.perf_counter() - feature_start) * 1000
                logger.debug(f"Audit: Feature '{name}' computed successfully in {feature_duration:.2f}ms.")
            except Exception as e:
                error_msg = f"Fatal transformation sequence abort at '{name}': {e}"
                logger.error(error_msg)
                raise FeatureTransformationError(error_msg) from e
                
        # Finalized feature union
        result_df: pd.DataFrame = pd.DataFrame(transformed_data)
        
        total_duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Transformation sequence finalized. "
            f"Audited {len(feature_names)} features in {total_duration:.2f}ms."
        )
        
        return result_df
