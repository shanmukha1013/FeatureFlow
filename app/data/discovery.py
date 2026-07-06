import os
import glob
import pandas as pd
import hashlib
import time
from typing import Dict, Any, List
from datetime import datetime

from app.config import settings
from app.utils.logger import get_logger
from app.data.dataset_registry import global_dataset_registry, DatasetMetadata
from app.monitoring.audit import AuditLogger, AuditEvent
from app.data.loader import CSVDataLoader
from app.data.validator import DataValidator
from app.data.profiler import DataProfiler
from app.data.flexy_registry import registry as schema_registry

logger = get_logger(__name__)

class DatasetDiscovery:
    """
    Automatically discovers, registers, validates, and profiles datasets.
    """
    def __init__(self, data_dir: str = settings.data_dir) -> None:
        self.data_dir = os.path.abspath(data_dir)
        self.loader = CSVDataLoader(data_dir=self.data_dir)
        self.profiler = DataProfiler()

    def _calculate_checksum(self, file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    def _process_dataset(self, metadata: DatasetMetadata, file_name: str, dataset_name: str) -> None:
        """Executes Validation and Profiling on a registered dataset."""
        import traceback
        from app.pipelines.pipeline import _pipeline_history
        from app.pipelines.execution_context import PipelineExecutionReport, DatasetExecutionReport
        
        # 0. Initialize Pipeline Logging
        pipeline_report = PipelineExecutionReport(pipeline_name="Automated ML Pipeline")
        ds_report = DatasetExecutionReport(dataset_name=dataset_name)
        pipeline_report.dataset_reports[dataset_name] = ds_report
        
        start_time = time.time()
        try:
            # 1. Load Data
            df = self.loader.load(metadata.relative_path)
            
            # 2. Validate Data
            schema = schema_registry.get(dataset_name)
            validator = DataValidator(schema=schema)
            val_report = validator.validate(df)
            ds_report.validation_report = val_report
            
            metadata.validation_status = "VALID" if val_report.is_valid else "INVALID"
            metadata.schema_status = "COMPLETED" if val_report.is_valid else "MISMATCH"
            
            # Parse duplicate warnings to update metadata
            metadata.duplicate_count = 0
            for w in val_report.warnings:
                if "duplicate rows" in w.lower():
                    try:
                        metadata.duplicate_count = int([word for word in w.split() if word.isdigit()][0])
                    except: pass
            
            AuditLogger.record(AuditEvent(
                event_name="DATASET_VALIDATED",
                component="DatasetDiscovery",
                severity="INFO",
                payload={"dataset_id": metadata.dataset_id, "is_valid": val_report.is_valid}
            ))
            
            # 3. Profile Data
            prof_report = self.profiler.profile(df)
            ds_report.profiling_report = prof_report
            
            metadata.profiling_status = "COMPLETED"
            metadata.last_profile_time = prof_report.generated_at.isoformat()
            
            if prof_report.null_percentages:
                metadata.null_percentage_max = max(prof_report.null_percentages.values()) * 100
            
            # Update memory dynamically based on exact profiling if desired
            metadata.estimated_memory_bytes = int(prof_report.memory_usage_mb * 1024 * 1024)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            AuditLogger.record(AuditEvent(
                event_name="PROFILING_COMPLETED",
                component="DatasetDiscovery",
                severity="INFO",
                payload={"dataset_id": metadata.dataset_id, "execution_time_ms": execution_time_ms, "rows_processed": prof_report.row_count}
            ))
            
            # 4. Feature Engineering Pipeline
            from app.features.engine import FeatureEngineeringEngine
            feature_engine = FeatureEngineeringEngine()
            feature_engine.execute(metadata)
            
            # 5. Training Orchestration Pipeline
            from app.training.orchestrator import TrainingOrchestrator
            trainer = TrainingOrchestrator(data_dir=self.data_dir)
            trainer.execute(metadata)
            
            # Mark Success
            ds_report.mark_success()
            pipeline_report.mark_complete()
            _pipeline_history.insert(0, pipeline_report)
            
        except Exception as e:
            error_msg = f"{e}\n{traceback.format_exc()}"
            logger.error(f"Failed to process dataset {dataset_name}: {error_msg}")
            
            # Mark Failure
            ds_report.mark_failure(error_msg)
            pipeline_report.mark_complete()
            _pipeline_history.insert(0, pipeline_report)
            
            if "validation" in error_msg.lower() or "schema" in error_msg.lower():
                metadata.validation_status = "FAILED"
                AuditLogger.record(AuditEvent(
                    event_name="VALIDATION_FAILED",
                    component="DatasetDiscovery",
                    severity="ERROR",
                    payload={"dataset_id": metadata.dataset_id, "error": error_msg}
                ))
            else:
                metadata.profiling_status = "FAILED"
                AuditLogger.record(AuditEvent(
                    event_name="PROFILING_FAILED",
                    component="DatasetDiscovery",
                    severity="ERROR",
                    payload={"dataset_id": metadata.dataset_id, "error": error_msg}
                ))

    def discover_datasets(self) -> List[DatasetMetadata]:
        logger.info(f"Initiating dataset discovery in '{self.data_dir}'.")
        
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory '{self.data_dir}' does not exist.")
            return []

        discovered: List[DatasetMetadata] = []
        
        # Recursively scan for .csv files
        search_pattern = os.path.join(self.data_dir, "**", "*.csv")
        csv_files = glob.glob(search_pattern, recursive=True)

        for file_path in csv_files:
            file_name = os.path.basename(file_path)
            dataset_name = os.path.splitext(file_name)[0]
            
            # Emit Dataset Discovered Event
            AuditLogger.record(AuditEvent(
                event_name="DATASET_DISCOVERED",
                component="DatasetDiscovery",
                severity="INFO",
                payload={"file_name": file_name, "path": file_path}
            ))

            try:
                stat = os.stat(file_path)
                
                # Introspect without loading full file
                sample_df = pd.read_csv(file_path, nrows=100)
                
                # Auto-register schema if missing
                if not schema_registry.has_schema(dataset_name):
                    from app.data.schema import DatasetSchema, ColumnSchema
                    columns = []
                    for col, dtype in sample_df.dtypes.items():
                        col_type = "int64" if "int" in str(dtype) else "float64" if "float" in str(dtype) else "object"
                        columns.append(ColumnSchema(name=str(col), dtype=col_type))
                    
                    entity_id = f"{dataset_name[:-1]}_id" if dataset_name.endswith('s') else f"{dataset_name}_id"
                    if entity_id not in sample_df.columns:
                        entity_id = sample_df.columns[0]

                    schema = DatasetSchema(name=dataset_name, columns=columns, entity_id_column=entity_id)
                    schema_registry.register(schema)
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    row_count = sum(1 for _ in f) - 1 # subtract header
                
                # Memory estimation (sample memory / sample rows * total rows)
                sample_mem = sample_df.memory_usage(deep=True).sum()
                avg_row_mem = sample_mem / len(sample_df) if len(sample_df) > 0 else 0
                estimated_memory = int(avg_row_mem * row_count)
                
                inferred_dtypes = {col: str(dtype) for col, dtype in sample_df.dtypes.items()}
                
                checksum = self._calculate_checksum(file_path)
                now_iso = datetime.utcnow().isoformat()
                
                metadata = DatasetMetadata(
                    dataset_id=f"ds_{checksum[:8]}_{dataset_name}",
                    dataset_name=dataset_name,
                    absolute_path=file_path,
                    relative_path=os.path.relpath(file_path, self.data_dir),
                    file_size=stat.st_size,
                    created_time=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    extension=".csv",
                    status="REGISTERED",
                    discovery_timestamp=now_iso,
                    registration_timestamp=now_iso,
                    source_type="CSV",
                    version="1.0.0",
                    checksum=checksum,
                    row_count=row_count,
                    column_count=len(sample_df.columns),
                    column_names=list(sample_df.columns),
                    inferred_dtypes=inferred_dtypes,
                    estimated_memory_bytes=estimated_memory
                )
                
                global_dataset_registry.register(metadata)
                discovered.append(metadata)
                
                # Emit Dataset Registered Event
                AuditLogger.record(AuditEvent(
                    event_name="DATASET_REGISTERED",
                    component="DatasetDiscovery",
                    severity="INFO",
                    payload={"dataset_id": metadata.dataset_id, "dataset_name": dataset_name}
                ))

                logger.info(f"Introspected and registered dataset: '{dataset_name}'")
                
                # Trigger Pipeline: Validate & Profile
                self._process_dataset(metadata, file_name, dataset_name)
                
            except Exception as e:
                import traceback
                error_msg = f"{e}\n{traceback.format_exc()}"
                logger.error(f"Error during discovery of {file_path}: {error_msg}")
                # Emit Dataset Loading Failed Event
                AuditLogger.record(AuditEvent(
                    event_name="DATASET_LOADING_FAILED",
                    component="DatasetDiscovery",
                    severity="ERROR",
                    payload={"file_name": file_name, "path": file_path, "error": error_msg}
                ))
                
        logger.info(f"Discovery complete. Found {len(discovered)} datasets.")
        return discovered
