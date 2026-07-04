"""
Defines abstract contracts for orchestrating pipelines.

Enforces a standard execution interface ensuring that all pipelines 
can be seamlessly swapped, tested, and tracked.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.pipelines.execution_context import PipelineExecutionReport

class BasePipeline(ABC):
    """
    Abstract contract for an executable pipeline workflow.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the semantic name of the pipeline."""
        ...
        
    @abstractmethod
    def run(self, datasets: Optional[List[str]] = None) -> PipelineExecutionReport:
        """
        Executes the pipeline flow.
        
        Args:
            datasets: Optional list of dataset names to restrict processing.
                      If None, the pipeline should dynamically process all available targets.
                      
        Returns:
            A consolidated PipelineExecutionReport containing success/failure telemetry.
        """
        ...
