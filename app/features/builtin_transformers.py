import pandas as pd
import numpy as np
from typing import Any
from app.features.feature import BaseFeature

# =======================
# NUMERIC TRANSFORMATIONS
# =======================

class PassthroughFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        return {}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col]

    def transform_single(self, data: dict) -> Any:
        col = self.metadata.source_columns[0]
        return data.get(col)



class StandardScalerFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        col = self.metadata.source_columns[0]
        mean = float(df[col].mean()) if not df[col].empty else 0.0
        std = float(df[col].std()) if not df[col].empty else 1.0
        return {"mean": mean, "std": std if std != 0 else 1.0}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        state = getattr(self.metadata, 'state', {})
        mean = state.get("mean", 0.0)
        std = state.get("std", 1.0)
        return (df[col] - mean) / std

    def transform_single(self, data: dict) -> float:
        col = self.metadata.source_columns[0]
        val = float(data.get(col, 0.0))
        state = getattr(self.metadata, 'state', {})
        mean = state.get("mean", 0.0)
        std = state.get("std", 1.0)
        return float((val - mean) / std)


class MinMaxFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        col = self.metadata.source_columns[0]
        cmin = float(df[col].min()) if not df[col].empty else 0.0
        cmax = float(df[col].max()) if not df[col].empty else 1.0
        return {"min": cmin, "max": cmax, "range": (cmax - cmin) if cmax != cmin else 1.0}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        state = getattr(self.metadata, 'state', {})
        cmin = state.get("min", 0.0)
        rng = state.get("range", 1.0)
        return (df[col] - cmin) / rng

    def transform_single(self, data: dict) -> float:
        col = self.metadata.source_columns[0]
        val = float(data.get(col, 0.0))
        state = getattr(self.metadata, 'state', {})
        cmin = state.get("min", 0.0)
        rng = state.get("range", 1.0)
        return float((val - cmin) / rng)


class RobustScalerFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        col = self.metadata.source_columns[0]
        median = float(df[col].median()) if not df[col].empty else 0.0
        q1 = float(df[col].quantile(0.25)) if not df[col].empty else 0.0
        q3 = float(df[col].quantile(0.75)) if not df[col].empty else 1.0
        return {"median": median, "iqr": (q3 - q1) if q3 != q1 else 1.0}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        state = getattr(self.metadata, 'state', {})
        median = state.get("median", 0.0)
        iqr = state.get("iqr", 1.0)
        return (df[col] - median) / iqr

    def transform_single(self, data: dict) -> float:
        col = self.metadata.source_columns[0]
        val = float(data.get(col, 0.0))
        state = getattr(self.metadata, 'state', {})
        median = state.get("median", 0.0)
        iqr = state.get("iqr", 1.0)
        return float((val - median) / iqr)


class LogTransformFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        return {}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return np.log1p(df[col].clip(lower=0))

    def transform_single(self, data: dict) -> float:
        col = self.metadata.source_columns[0]
        val = max(0.0, float(data.get(col, 0.0)))
        return float(np.log1p(val))


class NormalizationFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        col = self.metadata.source_columns[0]
        norm = float(df[col].pow(2).sum() ** 0.5) if not df[col].empty else 1.0
        return {"norm": norm if norm != 0 else 1.0}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        state = getattr(self.metadata, 'state', {})
        norm = state.get("norm", 1.0)
        return df[col] / norm

    def transform_single(self, data: dict) -> float:
        col = self.metadata.source_columns[0]
        val = float(data.get(col, 0.0))
        state = getattr(self.metadata, 'state', {})
        norm = state.get("norm", 1.0)
        return float(val / norm)


# =======================
# CATEGORICAL TRANSFORMATIONS
# =======================


class LabelEncodingFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        col = self.metadata.source_columns[0]
        unique_vals = df[col].dropna().unique().tolist()
        mapping = {str(val): i for i, val in enumerate(unique_vals)}
        return {"mapping": mapping}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        state = getattr(self.metadata, 'state', {})
        mapping = state.get("mapping", {})
        return df[col].astype(str).map(mapping).fillna(-1).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        val = str(data.get(col, ""))
        state = getattr(self.metadata, 'state', {})
        mapping = state.get("mapping", {})
        return int(mapping.get(val, -1))


class FrequencyEncodingFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        col = self.metadata.source_columns[0]
        freq = df[col].value_counts(normalize=True).to_dict()
        freq = {str(k): float(v) for k, v in freq.items()}
        return {"freq": freq}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        state = getattr(self.metadata, 'state', {})
        freq = state.get("freq", {})
        return df[col].astype(str).map(freq).fillna(0.0)

    def transform_single(self, data: dict) -> float:
        col = self.metadata.source_columns[0]
        val = str(data.get(col, ""))
        state = getattr(self.metadata, 'state', {})
        freq = state.get("freq", {})
        return float(freq.get(val, 0.0))


class OneHotEncodingFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        col = self.metadata.source_columns[0]
        top_cat = str(df[col].mode()[0]) if not df[col].empty else ""
        return {"top_cat": top_cat}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        state = getattr(self.metadata, 'state', {})
        top_cat = state.get("top_cat", "")
        return (df[col].astype(str) == top_cat).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        val = str(data.get(col, ""))
        state = getattr(self.metadata, 'state', {})
        top_cat = state.get("top_cat", "")
        return int(val == top_cat)


# =======================
# DATETIME TRANSFORMATIONS
# =======================

class DatetimeBaseFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        return {}


class DatetimeYearFeature(DatetimeBaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.year.fillna(0).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        try:
            return int(pd.to_datetime(data.get(col)).year)
        except Exception:
            return 0


class DatetimeMonthFeature(DatetimeBaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.month.fillna(0).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        try:
            return int(pd.to_datetime(data.get(col)).month)
        except Exception:
            return 0


class DatetimeDayFeature(DatetimeBaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.day.fillna(0).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        try:
            return int(pd.to_datetime(data.get(col)).day)
        except Exception:
            return 0


class DatetimeHourFeature(DatetimeBaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.hour.fillna(0).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        try:
            return int(pd.to_datetime(data.get(col)).hour)
        except Exception:
            return 0


class DatetimeWeekdayFeature(DatetimeBaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.dayofweek.fillna(0).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        try:
            return int(pd.to_datetime(data.get(col)).dayofweek)
        except Exception:
            return 0


class DatetimeWeekendFeature(DatetimeBaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        dt = pd.to_datetime(df[col], errors='coerce')
        return dt.dt.dayofweek.isin([5, 6]).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        try:
            return int(pd.to_datetime(data.get(col)).dayofweek in [5, 6])
        except Exception:
            return 0


class DatetimeQuarterFeature(DatetimeBaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.quarter.fillna(0).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        try:
            return int(pd.to_datetime(data.get(col)).quarter)
        except Exception:
            return 0


# =======================
# BOOLEAN TRANSFORMATIONS
# =======================

class BinaryConversionFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        return {}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(bool).astype(int)

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        return int(bool(data.get(col, False)))


# =======================
# TEXT TRANSFORMATIONS
# =======================


class TextLengthFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        return {}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(str).str.len()

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        return len(str(data.get(col, "")))


class TextWordCountFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        return {}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(str).str.split().str.len()

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        return len(str(data.get(col, "")).split())


class TextCharacterCountFeature(BaseFeature):
    def fit(self, df: pd.DataFrame) -> dict:
        return {}

    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(str).str.replace(r"\s+", "", regex=True).str.len()

    def transform_single(self, data: dict) -> int:
        col = self.metadata.source_columns[0]
        import re
        s = str(data.get(col, ""))
        return len(re.sub(r"\s+", "", s))
