import pandas as pd
from typing import Dict, Any


class BaselineProfiler:
    """
    Extracts a statistical baseline profile from training data.
    """
    @staticmethod
    def compute_baseline(X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        baseline = {}

        # Features
        for col in X.columns:
            series = X[col]
            if pd.api.types.is_numeric_dtype(series):
                baseline[col] = {
                    "type": "numeric",
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "median": float(series.median()),
                    "q25": float(series.quantile(0.25)),
                    "q75": float(series.quantile(0.75)),
                    "missing_rate": float(series.isnull().mean()),
                    "unique_count": int(series.nunique())
                }
            else:
                baseline[col] = {
                    "type": "categorical",
                    "missing_rate": float(series.isnull().mean()),
                    "unique_count": int(series.nunique()),
                    "frequencies": series.value_counts(normalize=True).to_dict()
                }

        # Target
        if pd.api.types.is_numeric_dtype(y):
            baseline["_target"] = {
                "type": "numeric",
                "mean": float(y.mean()),
                "std": float(y.std())
            }
        else:
            baseline["_target"] = {
                "type": "categorical",
                "frequencies": y.value_counts(normalize=True).to_dict()
            }

        return baseline
