"""
End-to-End Orchestrator for FeatureFlow.

Coordinates the Data, Feature, and Storage layers to automatically process
discovered datasets into materialized features without leaking domain logic.
"""
from typing import List, Optional
import pandas as pd

from app.pipelines.base import BasePipeline
from app.pipelines.execution_context import PipelineExecutionReport, DatasetExecutionReport
from app.pipelines.exceptions import PipelineConfigurationError

_pipeline_history: List[PipelineExecutionReport] = []


from app.data.schema import SchemaRegistry
from app.data.discovery import DatasetDiscovery
from app.data.loader import CSVDataLoader
from app.data.validator import DataValidator
from app.data.profiler import DataProfiler
from app.data.preprocessor import DataPreprocessor
from app.features.registry import FeatureRegistry
from app.features.transformer import FeatureTransformer
from app.storage.manager import StorageManager
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FeatureMaterializationPipeline(BasePipeline):
    """
    Orchestrates the complete flow from raw dataset ingestion to persisted feature vectors.
    """
    def __init__(
        self,
        schema_registry: SchemaRegistry,
        feature_registry: FeatureRegistry,
        storage_manager: StorageManager,
        dataset_discovery: DatasetDiscovery,
        loader: CSVDataLoader,
        preprocessor: DataPreprocessor,
        profiler: DataProfiler
    ) -> None:
        if not all([schema_registry, feature_registry, storage_manager, dataset_discovery, loader, preprocessor, profiler]):
            raise PipelineConfigurationError("Pipeline initialization failed: Missing required layer dependencies.")
            
        self.schema_registry = schema_registry
        self.feature_registry = feature_registry
        self.storage_manager = storage_manager
        self.discovery = dataset_discovery
        self.loader = loader
        self.preprocessor = preprocessor
        self.profiler = profiler
        self.transformer = FeatureTransformer(self.feature_registry)

    @property
    def name(self) -> str:
        return "FeatureMaterializationPipeline"

    def run(self, datasets: Optional[List[str]] = None) -> PipelineExecutionReport:
        """
        Executes the pipeline for discovered or explicitly requested datasets.
        """
        report = PipelineExecutionReport(pipeline_name=self.name)
        logger.info(f"Pipeline '{self.name}' execution started.")
        
        discovered_targets = self.discovery.discover_datasets()
        
        # Filter if explicit datasets requested
        if datasets is not None:
            targets_to_process = {k: v for k, v in discovered_targets.items() if k in datasets}
        else:
            targets_to_process = discovered_targets

        if not targets_to_process:
            logger.warning("Pipeline executed but no valid target datasets were found.")
            report.mark_complete()
            return report

        for dataset_name, file_name in targets_to_process.items():
            dataset_report = DatasetExecutionReport(dataset_name=dataset_name)
            report.dataset_reports[dataset_name] = dataset_report
            
            try:
                self._process_dataset(dataset_name, file_name, dataset_report)
                dataset_report.mark_success()
                logger.info(f"Pipeline successfully completed dataset '{dataset_name}'.")
            except Exception as e:
                # Catch-all strictly to ensure failure in one dataset does not crash the entire pipeline batch
                error_msg = f"Pipeline execution failed for dataset '{dataset_name}': {e}"
                logger.error(error_msg)
                dataset_report.mark_failure(error_msg)

        report.mark_complete()
        logger.info(
            f"Pipeline '{self.name}' finalized in {report.total_duration_ms:.2f}ms. "
            f"Overall Status: {'SUCCESS' if report.is_successful else 'FAILED (Partial or Complete)'}"
        )
        _pipeline_history.insert(0, report)
        return report
    def _process_dataset(self, dataset_name: str, file_name: str, report: DatasetExecutionReport) -> None:
        """Internal E2E execution flow for a single dataset."""
        logger.info(f"--- Pipeline Phase: Processing Dataset '{dataset_name}' ---")
        
        # 1. Fetch strict schema contract
        schema = self.schema_registry.get(dataset_name)
        
        # 2. Data Layer Execution
        df = self.loader.load(file_name)
        
        validator = DataValidator(schema=schema)
        validation_result = validator.validate(df)
        report.validation_report = validation_result
        
        profiling_result = self.profiler.profile(df)
        report.profiling_report = profiling_result
        
        df_clean = self.preprocessor.process(df)
        
        # 3. Feature Layer Execution
        # We determine applicable features generically. In a production state, 
        # features explicitly declare their parent dataset namespace in metadata.
        # Here we map features that require the dataset's entity_id.
        applicable_features = []
        for feat_name in self.feature_registry.list_features():
            feat = self.feature_registry.get(feat_name)
            if schema.entity_id_column in feat.metadata.source_columns:
                applicable_features.append(feat_name)
                
        if not applicable_features:
            logger.warning(f"No features registered for dataset '{dataset_name}'. Bypassing Feature and Storage layers.")
            return

        feature_df = self.transformer.transform(df_clean, applicable_features)
        
        # Safely carry over the primary key required for storage
        if schema.entity_id_column not in feature_df.columns:
            feature_df[schema.entity_id_column] = df_clean[schema.entity_id_column]
            
        report.feature_count = len(applicable_features)

        # 4. Storage Layer Execution
        # Update the facade's entity mapping configuration for the current dataset namespace
        self.storage_manager.entity_id_column = schema.entity_id_column
        
        storage_meta = self.storage_manager.save_features(
            dataset_name=dataset_name, 
            df=feature_df, 
            version=schema.version, 
            sync_online=True
        )
        report.storage_metadata = storage_meta
