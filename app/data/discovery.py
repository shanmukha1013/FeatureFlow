import os
import glob
import pandas as pd
import hashlib
import time
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from app.storage.database import AsyncSessionLocal
from app.config import settings
from app.utils.logger import get_logger
from app.monitoring.audit import AuditLogger, AuditEvent
from app.data.loader import CSVDataLoader
from app.data.validator import DataValidator
from app.data.profiler import DataProfiler
from app.data.schema import global_schema_registry as schema_registry, DatasetSchema, ColumnSchema
from app.storage.repositories.core import DatasetRepository
from app.storage.models import Dataset

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
        
    async def _process_dataset(self, session: AsyncSession, dataset_record: Dataset, relative_path: str, dataset_name: str) -> None:
        """Executes Validation and Profiling on a registered dataset."""
        import traceback
        
        start_time = time.time()
        # 1. Load Data
        df = self.loader.load(relative_path)
        
        # 2. Validate Data
        if schema_registry.has_schema(dataset_name):
            schema = schema_registry.get(dataset_name)
        else:
            # Generic schema inferred dynamically from dataset for generic domain-agnostic validation
            cols = [ColumnSchema(col, str(df[col].dtype), required=False) for col in df.columns]
            schema = DatasetSchema(name=dataset_name, columns=cols, entity_id_column=df.columns[0] if len(df.columns) > 0 else "id")
            schema_registry.register(schema)
            
        validator = DataValidator(schema=schema)
        val_report = validator.validate(df)
        
        # Update metadata (Dataset) status
        dataset_record.status = "VALID" if val_report.is_valid else "INVALID"
        
        await AuditLogger.record(session, AuditEvent(
            event_name="DATASET_VALIDATED",
            component="DatasetDiscovery",
            severity="INFO",
            payload={"dataset_id": dataset_record.id, "is_valid": val_report.is_valid}
        ))
        
        # 3. Profile Data
        prof_report = self.profiler.profile(df)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        await AuditLogger.record(session, AuditEvent(
            event_name="PROFILING_COMPLETED",
            component="DatasetDiscovery",
            severity="INFO",
            payload={"dataset_id": dataset_record.id, "execution_time_ms": execution_time_ms, "rows_processed": prof_report.row_count}
        ))
        
        # Commit is deferred to the pipeline transaction
        
        # 4. Feature Engineering Pipeline
        from app.features.engine import FeatureEngineeringEngine
        feature_engine = FeatureEngineeringEngine()
        await feature_engine.execute(session, dataset_record)
        
        # 5. Training Orchestration Pipeline
        from app.training.orchestrator import TrainingOrchestrator
        trainer = TrainingOrchestrator(data_dir=self.data_dir)
        await trainer.execute(session, dataset_record, relative_path)

    async def _async_discover_datasets(self) -> List[Dataset]:
        logger.info(f"Initiating dataset discovery in '{self.data_dir}'.")
        
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory '{self.data_dir}' does not exist.")
            return []

        discovered: List[Dataset] = []
        
        search_pattern = os.path.join(self.data_dir, "**", "*.csv")
        csv_files = glob.glob(search_pattern, recursive=True)

        async with AsyncSessionLocal() as session:
            repo = DatasetRepository(session)
            
            for file_path in csv_files:
                file_name = os.path.basename(file_path)
                dataset_name = os.path.splitext(file_name)[0]
                
                await AuditLogger.record(session, AuditEvent(
                    event_name="DATASET_DISCOVERED",
                    component="DatasetDiscovery",
                    severity="INFO",
                    payload={"file_name": file_name, "path": file_path}
                ))

                try:
                    stat = os.stat(file_path)
                    
                    # Introspect
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
                        row_count = sum(1 for _ in f) - 1
                    
                    inferred_dtypes = {col: str(dtype) for col, dtype in sample_df.dtypes.items()}
                    
                    checksum = self._calculate_checksum(file_path)
                    
                    existing_dataset = await repo.get_by_name(dataset_name)
                    if not existing_dataset:
                        new_dataset = await repo.create({
                            "name": dataset_name,
                            "description": f"Auto-discovered dataset: {file_name}",
                            "inferred_dtypes": inferred_dtypes,
                            "status": "REGISTERED"
                        })
                        dataset_record = new_dataset
                    else:
                        dataset_record = existing_dataset
                        # Update dtypes if missing
                        if not dataset_record.inferred_dtypes:
                            dataset_record.inferred_dtypes = inferred_dtypes
                        
                    discovered.append(dataset_record)
                    
                    await AuditLogger.record(session, AuditEvent(
                        event_name="DATASET_REGISTERED",
                        component="DatasetDiscovery",
                        severity="INFO",
                        payload={"dataset_id": dataset_record.id, "dataset_name": dataset_name}
                    ))
                    
                    # Commit dataset creation before processing is deferred

                    logger.info(f"Introspected and registered dataset: '{dataset_name}'")
                    
                    # Trigger Pipeline
                    relative_path = os.path.relpath(file_path, self.data_dir)
                    await self._process_dataset(session, dataset_record, relative_path, dataset_name)
                    
                    # Transaction Commit for the entire pipeline of this dataset
                    await session.commit()
                    
                except Exception as e:
                    import traceback
                    error_msg = f"{e}\n{traceback.format_exc()}"
                    logger.error(f"Error during discovery of {file_path}: {error_msg}")
                    await session.rollback()
                    
                    await AuditLogger.record(session, AuditEvent(
                        event_name="DATASET_LOADING_FAILED",
                        component="DatasetDiscovery",
                        severity="ERROR",
                        payload={"file_name": file_name, "path": file_path, "error": error_msg}
                    ))
                    await session.commit()
                    
        logger.info(f"Discovery complete. Found {len(discovered)} datasets.")
        return discovered

    def discover_datasets(self) -> None:
        """Synchronous wrapper for async discovery."""
        asyncio.run(self._async_discover_datasets())
