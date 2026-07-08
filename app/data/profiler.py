"""
Generates statistical profiles for raw datasets.

Extracts deep diagnostic metrics (cardinality, null rates, numeric distributions) 
without mutating the underlying data structure.
"""
import pandas as pd
from typing import Dict
from dataclasses import dataclass
from datetime import datetime, timezone

from app.utils.logger import get_logger
from app.data.exceptions import DataProfilingError

logger = get_logger(__name__)

@dataclass(frozen=True)
class ProfilingReport:
    """
    Immutable, structured report detailing deep dataset statistics.
    """
    generated_at: datetime
    row_count: int
    column_count: int
    memory_usage_mb: float
    missing_values: Dict[str, int]
    null_percentages: Dict[str, float]
    data_types: Dict[str, str]
    cardinality: Dict[str, int]
    numerical_summaries: Dict[str, Dict[str, float]]

class DataProfiler:
    """
    Analyzes Pandas DataFrames to generate statistical profiles.
    """
    
    def profile(self, df: pd.DataFrame) -> ProfilingReport:
        """
        Executes a comprehensive statistical analysis on the provided DataFrame.
        
        Args:
            df: The validated Pandas DataFrame to analyze.
            
        Returns:
            A ProfilingReport object detailing the data distribution.
            
        Raises:
            DataProfilingError: If the analysis fails due to malformed data types.
        """
        if df is None or df.empty:
            raise DataProfilingError("Cannot profile an empty or None DataFrame.")

        try:
            logger.info("Initiating deep dataset profiling.")
            
            row_count: int = len(df)
            column_count: int = len(df.columns)
            
            # Deep memory inspection is expensive but necessary for platform constraints
            memory_usage: float = df.memory_usage(deep=True).sum() / (1024 * 1024)
            
            missing_values: Dict[str, int] = df.isnull().sum().to_dict()
            null_percentages: Dict[str, float] = (df.isnull().sum() / row_count).to_dict()
            
            data_types: Dict[str, str] = {col: str(dtype) for col, dtype in df.dtypes.items()}
            cardinality: Dict[str, int] = df.nunique().to_dict()
            
            # Extract standard numerical summaries strictly for numeric columns
            numeric_df: pd.DataFrame = df.select_dtypes(include=['number'])
            numerical_summaries: Dict[str, Dict[str, float]] = {}
            
            if not numeric_df.empty:
                desc_dict = numeric_df.describe().to_dict()
                numerical_summaries = {
                    col: {
                        "mean": float(stats.get("mean", 0.0)),
                        "std": float(stats.get("std", 0.0)),
                        "min": float(stats.get("min", 0.0)),
                        "max": float(stats.get("max", 0.0)),
                    }
                    for col, stats in desc_dict.items()
                }

            report = ProfilingReport(
                generated_at=datetime.now(timezone.utc),
                row_count=row_count,
                column_count=column_count,
                memory_usage_mb=round(memory_usage, 2),
                missing_values=missing_values,
                null_percentages=null_percentages,
                data_types=data_types,
                cardinality=cardinality,
                numerical_summaries=numerical_summaries
            )
            
            logger.info("Dataset profiling completed successfully.")
            return report
            
        except Exception as e:
            error_msg = f"Unexpected failure during dataset profiling: {e}"
            logger.error(error_msg)
            raise DataProfilingError(error_msg) from e
