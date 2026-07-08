import pandas as pd
import numpy as np
from app.features.feature import BaseFeature

# =======================
# NUMERIC TRANSFORMATIONS
# =======================
class StandardScalerFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        mean = df[col].mean()
        std = df[col].std()
        std = std if std != 0 else 1.0
        return (df[col] - mean) / std

class MinMaxFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        cmin = df[col].min()
        cmax = df[col].max()
        rng = cmax - cmin if cmax != cmin else 1.0
        return (df[col] - cmin) / rng

class RobustScalerFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1 if q3 != q1 else 1.0
        return (df[col] - df[col].median()) / iqr

class LogTransformFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        # Adding small epsilon to avoid log(0)
        return np.log1p(df[col].clip(lower=0))

class NormalizationFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        norm = df[col].pow(2).sum() ** 0.5
        norm = norm if norm != 0 else 1.0
        return df[col] / norm

# =======================
# CATEGORICAL TRANSFORMATIONS
# =======================
class LabelEncodingFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype('category').cat.codes

class FrequencyEncodingFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        freq = df[col].value_counts(normalize=True)
        return df[col].map(freq).fillna(0)

class OneHotEncodingFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        # Note: One-hot theoretically produces multiple columns, but for BaseFeature constraints, 
        # we'll return a top-1 category match as a binary series for simplicity, 
        # or just dummy encode the most frequent category.
        col = self.metadata.source_columns[0]
        top_cat = df[col].mode()[0] if not df[col].empty else None
        return (df[col] == top_cat).astype(int)

# =======================
# DATETIME TRANSFORMATIONS
# =======================
class DatetimeYearFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.year.fillna(0).astype(int)

class DatetimeMonthFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.month.fillna(0).astype(int)

class DatetimeDayFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.day.fillna(0).astype(int)

class DatetimeHourFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.hour.fillna(0).astype(int)

class DatetimeWeekdayFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.dayofweek.fillna(0).astype(int)

class DatetimeWeekendFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        dt = pd.to_datetime(df[col], errors='coerce')
        return dt.dt.dayofweek.isin([5, 6]).astype(int)

class DatetimeQuarterFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return pd.to_datetime(df[col], errors='coerce').dt.quarter.fillna(0).astype(int)

# =======================
# BOOLEAN TRANSFORMATIONS
# =======================
class BinaryConversionFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(bool).astype(int)

# =======================
# TEXT TRANSFORMATIONS
# =======================
class TextLengthFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(str).str.len()

class TextWordCountFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(str).str.split().str.len()

class TextCharacterCountFeature(BaseFeature):
    def transform(self, df: pd.DataFrame) -> pd.Series:
        col = self.metadata.source_columns[0]
        return df[col].astype(str).str.replace(r'\s+', '', regex=True).str.len()
