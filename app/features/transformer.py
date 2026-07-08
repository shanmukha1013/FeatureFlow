"""
Executes feature computation workflows.
"""
import time
import pandas as pd
from typing import List, Dict

from app.features.exceptions import FeatureTransformationError
from app.utils.logger import get_logger
from app.storage.models import Feature
from app.features.engine import FEATURE_MAPPINGS
from app.features.metadata import FeatureMetadata

logger = get_logger(__name__)

class FeatureTransformer:
    """
    Coordinates the execution of multiple feature transformations over raw datasets.
    """
    def __init__(self) -> None:
        self.class_map = {}
        for category, mappings in FEATURE_MAPPINGS.items():
            for mapping in mappings:
                self.class_map[mapping['transformation']] = mapping['class']

    def transform(self, df: pd.DataFrame, features: List[Feature]) -> pd.DataFrame:
        if df is None or df.empty:
            raise FeatureTransformationError("Transformer requires a populated DataFrame context.")
            
        if not features:
            logger.warning("Transformation requested with an empty feature list. Returning empty DataFrame.")
            return pd.DataFrame()

        start_time = time.perf_counter()
        logger.info(f"Initiating transformation sequence for {len(features)} features.")
        
        transformed_data: Dict[str, pd.Series] = {}
        
        for feature_record in features:
            name = feature_record.name
            try:
                feature_start = time.perf_counter()
                
                col_name = None
                for col in df.columns:
                    if f"_{col}_" in name:
                        col_name = col
                        break
                if not col_name:
                    col_name = df.columns[0]
                    
                meta = FeatureMetadata(
                    feature_id=feature_record.id,
                    name=feature_record.name,
                    source_dataset=feature_record.dataset.name if feature_record.dataset else "",
                    source_columns=[col_name],
                    transformation=feature_record.transformation,
                    data_type=feature_record.dtype,
                    feature_type="Numeric", # Default
                    description="Auto-generated feature",
                    version="1.0.0",
                    owner="system"
                )
                
                feature_class = self.class_map.get(feature_record.transformation)
                if not feature_class:
                    raise FeatureTransformationError(f"Unknown transformation: {feature_record.transformation}")
                    
                feature_instance = feature_class(metadata=meta)
                series: pd.Series = feature_instance(df)
                
                series.name = feature_record.name
                transformed_data[feature_record.name] = series
                
                feature_duration = (time.perf_counter() - feature_start) * 1000
                logger.debug(f"Audit: Feature '{name}' computed successfully in {feature_duration:.2f}ms.")
            except Exception as e:
                error_msg = f"Fatal transformation sequence abort at '{name}': {e}"
                logger.error(error_msg)
                raise FeatureTransformationError(error_msg) from e
                
        result_df: pd.DataFrame = pd.DataFrame(transformed_data)
        
        total_duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Transformation sequence finalized. "
            f"Audited {len(features)} features in {total_duration:.2f}ms."
        )
        
        return result_df
