"""
Executes generic, structural cleaning on validated datasets.

Standardizes structures across datasets (e.g., lowercase columns, trimming
strings, deduplication) without delving into semantic feature engineering.
"""
import pandas as pd
import numpy as np

from app.utils.logger import get_logger
from app.data.exceptions import DataPreprocessingError

logger = get_logger(__name__)


class DataPreprocessor:
    """
    Provides safe, generic data cleaning operations for DataFrames.
    """

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes a standard sequence of cleaning operations.

        Operations preserve the original DataFrame's immutability by operating on a copy.

        Args:
            df: Validated Pandas DataFrame.

        Returns:
            A newly allocated, cleaned Pandas DataFrame.

        Raises:
            DataPreprocessingError: If a cleaning operation fails unexpectedly.
        """
        if df is None or df.empty:
            raise DataPreprocessingError("Cannot preprocess an empty or None DataFrame.")

        try:
            logger.info("Initiating generic data preprocessing pipeline.")

            clean_df: pd.DataFrame = df.copy()
            clean_df = self._normalize_column_names(clean_df)
            clean_df = self._remove_duplicates(clean_df)
            clean_df = self._trim_whitespace(clean_df)
            clean_df = self._standardize_nulls(clean_df)

            logger.info("Generic data preprocessing pipeline completed successfully.")
            return clean_df

        except Exception as e:
            error_msg = f"Unexpected failure during generic preprocessing: {e}"
            logger.error(error_msg)
            raise DataPreprocessingError(error_msg) from e

    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Forces all column names to standard lowercase snake_case."""
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(r'[^a-z0-9_]', '_', regex=True)
            .str.replace(r'_+', '_', regex=True)
        )
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strips exact duplicate rows from the dataset."""
        initial_len: int = len(df)
        df = df.drop_duplicates()
        dropped: int = initial_len - len(df)
        if dropped > 0:
            logger.info(f"Preprocessing action: Dropped {dropped} exact duplicate rows.")
        return df

    def _trim_whitespace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Removes trailing/leading whitespace exclusively from string columns."""
        string_cols = df.select_dtypes(include=['object']).columns
        for col in string_cols:
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
        return df

    def _standardize_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converts whitespace-only strings directly to standard numpy NaNs."""
        df = df.replace(r'^\s*$', np.nan, regex=True)
        return df
