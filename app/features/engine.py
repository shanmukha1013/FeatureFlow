import uuid
import time
from datetime import datetime
from typing import List, Dict, Type

from app.utils.logger import get_logger
from app.data.dataset_registry import DatasetMetadata
from app.features.registry import global_feature_registry
from app.features.metadata import FeatureMetadata
from app.features.feature import BaseFeature
from app.monitoring.audit import AuditLogger, AuditEvent
from app.features.builtin_transformers import (
    StandardScalerFeature, MinMaxFeature, RobustScalerFeature, LogTransformFeature, NormalizationFeature,
    LabelEncodingFeature, FrequencyEncodingFeature, OneHotEncodingFeature,
    DatetimeYearFeature, DatetimeMonthFeature, DatetimeDayFeature, DatetimeHourFeature,
    DatetimeWeekdayFeature, DatetimeWeekendFeature, DatetimeQuarterFeature,
    BinaryConversionFeature,
    TextLengthFeature, TextWordCountFeature, TextCharacterCountFeature
)

logger = get_logger(__name__)

# Extensible mapping of primitive types to transformers
FEATURE_MAPPINGS: Dict[str, List[Dict[str, Any]]] = {
    "numeric": [
        {"class": StandardScalerFeature, "name": "standard_scaled", "transformation": "Standard Scaling", "dtype": "float64"},
        {"class": MinMaxFeature, "name": "minmax_scaled", "transformation": "Min-Max Scaling", "dtype": "float64"},
        {"class": RobustScalerFeature, "name": "robust_scaled", "transformation": "Robust Scaling", "dtype": "float64"},
        {"class": LogTransformFeature, "name": "log_transformed", "transformation": "Log Transform", "dtype": "float64"},
        {"class": NormalizationFeature, "name": "normalized", "transformation": "Normalization", "dtype": "float64"}
    ],
    "categorical": [
        {"class": LabelEncodingFeature, "name": "label_encoded", "transformation": "Label Encoding", "dtype": "int64"},
        {"class": FrequencyEncodingFeature, "name": "freq_encoded", "transformation": "Frequency Encoding", "dtype": "float64"},
        {"class": OneHotEncodingFeature, "name": "onehot_top", "transformation": "One Hot Encoding", "dtype": "int64"}
    ],
    "datetime": [
        {"class": DatetimeYearFeature, "name": "year", "transformation": "Year", "dtype": "int64"},
        {"class": DatetimeMonthFeature, "name": "month", "transformation": "Month", "dtype": "int64"},
        {"class": DatetimeDayFeature, "name": "day", "transformation": "Day", "dtype": "int64"},
        {"class": DatetimeHourFeature, "name": "hour", "transformation": "Hour", "dtype": "int64"},
        {"class": DatetimeWeekdayFeature, "name": "weekday", "transformation": "Weekday", "dtype": "int64"},
        {"class": DatetimeWeekendFeature, "name": "is_weekend", "transformation": "Weekend", "dtype": "int64"},
        {"class": DatetimeQuarterFeature, "name": "quarter", "transformation": "Quarter", "dtype": "int64"}
    ],
    "boolean": [
        {"class": BinaryConversionFeature, "name": "binary", "transformation": "Binary Conversion", "dtype": "int64"}
    ],
    "text": [
        {"class": TextLengthFeature, "name": "length", "transformation": "Length", "dtype": "int64"},
        {"class": TextWordCountFeature, "name": "word_count", "transformation": "Word Count", "dtype": "int64"},
        {"class": TextCharacterCountFeature, "name": "char_count", "transformation": "Character Count", "dtype": "int64"}
    ]
}

class FeatureEngineeringEngine:
    def __init__(self):
        pass

    def _determine_semantic_type(self, col: str, dtype: str) -> str:
        """Infers the semantic type for a given column based on naming heuristics and dtype."""
        dtype = dtype.lower()
        col_lower = col.lower()
        
        if "datetime" in dtype or "date" in col_lower or "time" in col_lower:
            return "datetime"
        if "bool" in dtype or "is_" in col_lower or "has_" in col_lower:
            return "boolean"
        if "int" in dtype or "float" in dtype:
            # If it has few unique values it might be categorical, but we don't have cardinality here 
            # so we map to numeric by default unless ID
            if col_lower.endswith("_id") or col_lower == "id":
                return "categorical"
            return "numeric"
        
        # Object/String
        if "description" in col_lower or "text" in col_lower or "comment" in col_lower:
            return "text"
        return "categorical"

    def execute(self, dataset_meta: DatasetMetadata) -> None:
        """
        Generates and registers features for a discovered dataset.
        """
        logger.info(f"Starting Feature Engineering for {dataset_meta.dataset_name}")
        start_time = time.time()
        
        features_generated = 0
        now_str = datetime.utcnow().isoformat()
        
        for col, dtype in dataset_meta.inferred_dtypes.items():
            semantic_type = self._determine_semantic_type(col, dtype)
            transformers = FEATURE_MAPPINGS.get(semantic_type, [])
            
            for transformer_info in transformers:
                feat_name = f"{dataset_meta.dataset_name}_{col}_{transformer_info['name']}"
                
                # Check for existing
                version = "1.0.0"
                if global_feature_registry.has_feature(feat_name):
                    # Bump version (naive implementation: increment minor)
                    existing = global_feature_registry.get(feat_name)
                    v_parts = existing.metadata.version.split('.')
                    version = f"{v_parts[0]}.{int(v_parts[1]) + 1}.0"
                    
                    AuditLogger.record(AuditEvent(
                        event_name="FEATURE_UPDATED",
                        component="FeatureEngine",
                        severity="INFO",
                        payload={"feature_name": feat_name, "new_version": version}
                    ))
                else:
                    AuditLogger.record(AuditEvent(
                        event_name="FEATURE_GENERATED",
                        component="FeatureEngine",
                        severity="INFO",
                        payload={"feature_name": feat_name}
                    ))
                
                feat_metadata = FeatureMetadata(
                    feature_id=str(uuid.uuid4()),
                    name=feat_name,
                    description=f"Auto-engineered feature via {transformer_info['transformation']} on {col}",
                    version=version,
                    owner="auto_feature_engine",
                    source_dataset=dataset_meta.dataset_name,
                    source_columns=[col],
                    feature_type=semantic_type.capitalize(),
                    transformation=transformer_info['transformation'],
                    data_type=transformer_info['dtype'],
                    status="ACTIVE",
                    created_at=now_str,
                    last_updated=now_str,
                    tags=["auto-engineered"]
                )
                
                try:
                    feat_instance = transformer_info['class'](metadata=feat_metadata)
                    
                    # Remove old version if updating
                    if global_feature_registry.has_feature(feat_name):
                        global_feature_registry.remove(feat_name)
                        
                    global_feature_registry.register(feat_instance)
                    features_generated += 1
                    
                    AuditLogger.record(AuditEvent(
                        event_name="FEATURE_REGISTERED",
                        component="FeatureEngine",
                        severity="INFO",
                        payload={"feature_id": feat_metadata.feature_id, "feature_name": feat_name}
                    ))
                except Exception as e:
                    AuditLogger.record(AuditEvent(
                        event_name="FEATURE_FAILED",
                        component="FeatureEngine",
                        severity="ERROR",
                        payload={"feature_name": feat_name, "error": str(e)}
                    ))
                    
        exec_time = int((time.time() - start_time) * 1000)
        AuditLogger.record(AuditEvent(
            event_name="FEATURE_EXECUTION_TIME",
            component="FeatureEngine",
            severity="INFO",
            payload={"dataset": dataset_meta.dataset_name, "features_engineered": features_generated, "time_ms": exec_time}
        ))
        logger.info(f"Feature Engineering complete for {dataset_meta.dataset_name}. Generated {features_generated} features in {exec_time}ms.")
