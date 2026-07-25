"""
Executes stateful feature computation workflows.
"""
import time
import pandas as pd
from typing import List, Dict, Any

from app.features.exceptions import FeatureTransformationError
from app.utils.logger import get_logger
from app.storage.models import Feature
from app.features.engine import FEATURE_MAPPINGS
from app.features.metadata import FeatureMetadata

logger = get_logger(__name__)


class FeatureTransformer:
    """
    Coordinates the execution of multiple feature transformations over raw datasets or single requests.
    Enforces training-serving consistency by using saved transformation states.
    """

    def __init__(self) -> None:
        self.class_map = {}
        for category, mappings in FEATURE_MAPPINGS.items():
            for mapping in mappings:
                self.class_map[mapping['transformation']] = mapping['class']

    def _build_metadata(self, df_or_dict, feature_record: Feature) -> FeatureMetadata:
        """Helper to construct strictly typed FeatureMetadata from DB records."""
        name = feature_record.name
        
        # Heuristic to find the original column name if not explicitly stored
        col_name = None
        if isinstance(df_or_dict, pd.DataFrame):
            for col in df_or_dict.columns:
                if f"_{col}_" in name:
                    col_name = col
                    break
            if not col_name and not df_or_dict.empty:
                col_name = df_or_dict.columns[0]
        else:
            for col in df_or_dict.keys():
                if f"_{col}_" in name:
                    col_name = col
                    break
            if not col_name and df_or_dict:
                col_name = list(df_or_dict.keys())[0]

        ds_name = ""
        try:
            if getattr(feature_record, "dataset", None):
                ds_name = feature_record.dataset.name
        except Exception:
            pass

        return FeatureMetadata(
            feature_id=feature_record.id,
            name=feature_record.name,
            source_dataset=ds_name,
            source_columns=[col_name] if col_name else [],
            transformation=feature_record.transformation,
            data_type=feature_record.dtype,
            feature_type="Numeric",
            description="Auto-generated feature",
            version=str(feature_record.version),
            owner="system",
            state=feature_record.state or {}
        )

    def fit(self, df: pd.DataFrame, features: List[Feature]) -> None:
        """
        Computes the canonical state for all features in the offline training dataset.
        Updates the feature_record.state in-memory. Caller must commit to DB.
        """
        if df is None or df.empty:
            raise FeatureTransformationError("Transformer requires a populated DataFrame context to fit.")

        logger.info(f"Initiating feature fitting sequence for {len(features)} features.")
        start_time = time.perf_counter()

        for feature_record in features:
            try:
                meta = self._build_metadata(df, feature_record)
                feature_class = self.class_map.get(feature_record.transformation)
                
                if not feature_class:
                    raise FeatureTransformationError(f"Unknown transformation: {feature_record.transformation}")

                feature_instance = feature_class(metadata=meta)
                
                # Compute state
                state_dict = feature_instance.fit(df)
                feature_record.state = state_dict

            except Exception as e:
                logger.error(f"Failed to fit feature '{feature_record.name}': {e}")
                raise FeatureTransformationError(f"Fit failed for {feature_record.name}") from e

        duration = (time.perf_counter() - start_time) * 1000
        logger.info(f"Fitting sequence completed in {duration:.2f}ms.")

    def transform(self, df: pd.DataFrame, features: List[Feature]) -> pd.DataFrame:
        """
        Applies canonical transformations to a batch DataFrame using pre-fitted state.
        """
        if df is None or df.empty:
            raise FeatureTransformationError("Transformer requires a populated DataFrame context.")

        if not features:
            logger.warning("Transformation requested with an empty feature list. Returning empty DataFrame.")
            return pd.DataFrame()

        start_time = time.perf_counter()
        logger.info(f"Initiating offline transformation sequence for {len(features)} features.")

        transformed_data: Dict[str, pd.Series] = {}

        for feature_record in features:
            name = feature_record.name
            try:
                meta = self._build_metadata(df, feature_record)
                feature_class = self.class_map.get(feature_record.transformation)
                if not feature_class:
                    raise FeatureTransformationError(f"Unknown transformation: {feature_record.transformation}")

                feature_instance = feature_class(metadata=meta)
                series: pd.Series = feature_instance(df)

                series.name = feature_record.name
                transformed_data[feature_record.name] = series

            except Exception as e:
                error_msg = f"Fatal transformation sequence abort at '{name}': {e}"
                logger.error(error_msg)
                raise FeatureTransformationError(error_msg) from e

        result_df: pd.DataFrame = pd.DataFrame(transformed_data)
        total_duration = (time.perf_counter() - start_time) * 1000
        logger.info(f"Transformation sequence finalized in {total_duration:.2f}ms.")
        return result_df

    def transform_single(self, raw_dict: Dict[str, Any], features: List[Feature]) -> Dict[str, Any]:
        """
        Applies canonical transformations to a single live prediction request.
        Uses pre-fitted state to guarantee Training-Serving consistency.
        """
        if not raw_dict:
            return {}

        if not features:
            return {}

        transformed_record: Dict[str, Any] = {}

        for feature_record in features:
            try:
                meta = self._build_metadata(raw_dict, feature_record)
                feature_class = self.class_map.get(feature_record.transformation)
                if not feature_class:
                    raise FeatureTransformationError(f"Unknown transformation: {feature_record.transformation}")

                feature_instance = feature_class(metadata=meta)
                canonical_value = feature_instance.transform_single(raw_dict)
                transformed_record[feature_record.name] = canonical_value

            except Exception as e:
                logger.error(f"Online transformation failed for '{feature_record.name}': {e}")
                # Provide strict fallback to prevent total inference failure, but skew will likely occur
                transformed_record[feature_record.name] = 0.0

        return transformed_record
