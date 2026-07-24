"""
Centralizes exceptions for the Pipeline & Orchestration layer.
"""


class PipelineError(Exception):
    """Base exception for all pipeline and orchestration errors."""


class PipelineConfigurationError(PipelineError):
    """Raised when a pipeline is instantiated with invalid configurations or missing dependencies."""


class PipelineExecutionError(PipelineError):
    """Raised when a pipeline completely halts execution unexpectedly."""
