"""
FeatureMaterializationPipeline: Orchestrates the full ML pipeline.

Discovers datasets, validates, profiles, engineers features, trains models,
and tracks experiments - all within PostgreSQL-backed transactions.
"""
from typing import Optional, List

from app.pipelines.base import BasePipeline
from app.pipelines.execution_context import PipelineExecutionReport, DatasetExecutionReport
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureMaterializationPipeline(BasePipeline):
    """
    End-to-end feature materialization and model training pipeline.
    
    Delegates to DatasetDiscovery which handles:
    - Dataset registration
    - Validation
    - Profiling
    - Feature engineering
    - Model training
    - Experiment tracking
    - Champion selection
    
    All metadata is persisted to PostgreSQL within atomic transactions.
    """

    @property
    def name(self) -> str:
        return "FeatureMaterializationPipeline"

    def run(self, datasets: Optional[List[str]] = None) -> PipelineExecutionReport:
        """
        Executes the full E2E pipeline synchronously.
        
        Internally wraps the async DatasetDiscovery pipeline in a sync runner
        for compatibility with synchronous callers (e.g., background threads).
        """
        import asyncio
        report = PipelineExecutionReport(pipeline_name=self.name)
        
        try:
            from app.data.discovery import DatasetDiscovery
            discovery = DatasetDiscovery()
            asyncio.run(discovery._async_discover_datasets())
            report.mark_complete()
            logger.info(f"Pipeline '{self.name}' completed successfully.")
        except Exception as e:
            logger.error(f"Pipeline '{self.name}' failed: {e}")
            report.mark_complete()
            
        return report
