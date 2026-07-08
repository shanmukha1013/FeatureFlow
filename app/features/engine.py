import time
from typing import List, Dict, Any

from app.utils.logger import get_logger
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
            if col_lower.endswith("_id") or col_lower == "id":
                return "categorical"
            return "numeric"
        
        if "description" in col_lower or "text" in col_lower or "comment" in col_lower:
            return "text"
        return "categorical"

    async def execute(self, session, dataset_record) -> None:
        """
        Generates and registers features for a discovered dataset.
        """
        from app.storage.repositories.core import FeatureRepository
        feature_repo = FeatureRepository(session)
        
        logger.info(f"Starting Feature Engineering for {dataset_record.name}")
        start_time = time.time()
        
        features_generated = 0
        
        dtypes_to_process = dataset_record.inferred_dtypes if dataset_record.inferred_dtypes else {}
        
        for col, dtype in dtypes_to_process.items():
            semantic_type = self._determine_semantic_type(col, dtype)
            transformers = FEATURE_MAPPINGS.get(semantic_type, [])
            
            for transformer_info in transformers:
                feat_name = f"{dataset_record.name}_{col}_{transformer_info['name']}"
                
                # Check for existing feature in DB
                from sqlalchemy.future import select
                from app.storage.models import Feature
                existing = await session.execute(
                    select(Feature).filter(Feature.dataset_id == dataset_record.id, Feature.name == feat_name)
                )
                existing_feat = existing.scalars().first()
                
                version = 1
                if existing_feat:
                    version = existing_feat.version + 1
                    existing_feat.version = version
                    existing_feat.dtype = transformer_info['dtype']
                    existing_feat.transformation = transformer_info['transformation']
                    
                    await AuditLogger.record(session, AuditEvent(
                        event_name="FEATURE_UPDATED",
                        component="FeatureEngine",
                        severity="INFO",
                        payload={"feature_name": feat_name, "new_version": version}
                    ))
                else:
                    new_feat = await feature_repo.create({
                        "dataset_id": dataset_record.id,
                        "name": feat_name,
                        "dtype": transformer_info['dtype'],
                        "transformation": transformer_info['transformation'],
                        "status": "ACTIVE"
                    })
                    
                    await AuditLogger.record(session, AuditEvent(
                        event_name="FEATURE_GENERATED",
                        component="FeatureEngine",
                        severity="INFO",
                        payload={"feature_name": feat_name, "feature_id": new_feat.id}
                    ))
                
                features_generated += 1
                
        # Commit all feature generations
        # Commit is deferred to the pipeline transaction
                    
        exec_time = int((time.time() - start_time) * 1000)
        await AuditLogger.record(session, AuditEvent(
            event_name="FEATURE_EXECUTION_TIME",
            component="FeatureEngine",
            severity="INFO",
            payload={"dataset": dataset_record.name, "features_engineered": features_generated, "time_ms": exec_time}
        ))
        # Ensure final audit log commits
        # Commit is deferred to the pipeline transaction
        
        logger.info(f"Feature Engineering complete for {dataset_record.name}. Generated {features_generated} features in {exec_time}ms.")
