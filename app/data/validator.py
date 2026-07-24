"""
Executes structural and quality validations on loaded datasets.

Ensures that the raw DataFrames conform strictly to defined `DatasetSchema`
contracts before they are permitted downstream, catching anomalies early.
"""
import pandas as pd
from typing import List
from dataclasses import dataclass, field

from app.utils.logger import get_logger
from app.data.schema import DatasetSchema
from app.data.exceptions import SchemaValidationError, DataValidationError

logger = get_logger(__name__)


@dataclass(frozen=True)
class ValidationReport:
    """
    Immutable summary of the validation execution.
    """
    schema_name: str
    schema_version: str
    is_valid: bool
    warnings: List[str] = field(default_factory=list)


class DataValidator:
    """
    Validates Pandas DataFrames against schemas and semantic quality rules.
    """

    def __init__(self, schema: DatasetSchema, max_null_percentage: float = 0.5) -> None:
        """
        Args:
            schema: The formal structural contract the dataset must fulfill.
            max_null_percentage: Threshold (0.0 to 1.0) above which nulls trigger warnings.
        """
        if not (0.0 <= max_null_percentage <= 1.0):
            raise ValueError("max_null_percentage must be between 0.0 and 1.0.")

        self.schema = schema
        self.max_null_percentage = max_null_percentage

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """
        Executes the full suite of validation rules on the dataset.

        Args:
            df: The raw Pandas DataFrame to validate.

        Returns:
            A ValidationReport detailing any warnings encountered.

        Raises:
            DataValidationError: If the dataset is empty or completely unprocessable.
            SchemaValidationError: If the dataset strictly violates structural requirements.
        """
        logger.info(f"Initiating validation for dataset schema: {self.schema.name} (v{self.schema.version})")

        self._check_empty(df)
        self._validate_schema(df)

        warnings: List[str] = []
        warnings.extend(self._check_duplicates(df))
        warnings.extend(self._check_nulls(df))

        logger.info(f"Dataset validation passed for '{self.schema.name}'. Generated {len(warnings)} warnings.")
        return ValidationReport(
            schema_name=self.schema.name,
            schema_version=self.schema.version,
            is_valid=True,
            warnings=warnings
        )

    def _check_empty(self, df: pd.DataFrame) -> None:
        """Fails fast if the dataset is completely devoid of rows or columns."""
        if df.empty:
            error_msg = "Dataset validation failed: Dataset is completely empty."
            logger.error(error_msg)
            raise DataValidationError(error_msg)

    def _validate_schema(self, df: pd.DataFrame) -> None:
        """Validates strict presence of required columns and loose dtype matching."""
        missing_cols: List[str] = [col for col in self.schema.required_columns if col not in df.columns]
        if missing_cols:
            error_msg = f"Schema violation. Missing required columns: {missing_cols}"
            logger.error(error_msg)
            raise SchemaValidationError(error_msg)

        for col_name, expected_dtype in self.schema.expected_dtypes.items():
            if col_name in df.columns:
                actual_dtype: str = str(df[col_name].dtype)
                # Allow flexible dtype matching to accommodate Pandas idiosyncrasies
                if expected_dtype not in actual_dtype and actual_dtype != 'object':
                    logger.warning(f"Type mismatch on '{col_name}': expected ~{expected_dtype}, got {actual_dtype}")

    def _check_duplicates(self, df: pd.DataFrame) -> List[str]:
        """Checks for exact row duplications across all columns."""
        warnings = []
        dup_count: int = int(df.duplicated().sum())
        if dup_count > 0:
            msg = f"Quality anomaly: Detected {dup_count} exact duplicate rows."
            logger.warning(msg)
            warnings.append(msg)
        return warnings

    def _check_nulls(self, df: pd.DataFrame) -> List[str]:
        """Evaluates column sparsity against the configured threshold."""
        warnings = []
        null_percentages: pd.Series = df.isnull().mean()
        for col, pct in null_percentages.items():
            if pct > self.max_null_percentage:
                msg = f"Sparsity anomaly: Column '{col}' exceeds null threshold ({pct:.1%} > {self.max_null_percentage:.1%})."
                logger.warning(msg)
                warnings.append(msg)
        return warnings
