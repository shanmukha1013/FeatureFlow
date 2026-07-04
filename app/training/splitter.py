"""
Partitions datasets into training and testing segments.
"""
import pandas as pd
from typing import Tuple

from app.training.base import BaseSplitter

class RandomSplitter(BaseSplitter):
    """
    Splits data deterministically using a random seed.
    """
    def __init__(self, test_size: float = 0.2, random_state: int = 42) -> None:
        self.test_size = test_size
        self.random_state = random_state
        
    def split(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        from sklearn.model_selection import train_test_split
        return train_test_split(X, y, test_size=self.test_size, random_state=self.random_state)

class TimeBasedSplitter(BaseSplitter):
    """
    Splits data based on temporal ordering without shuffling.
    Assumes the dataset is pre-sorted chronologically.
    """
    def __init__(self, test_size: float = 0.2) -> None:
        self.test_size = test_size
        
    def split(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        split_idx = int(len(X) * (1 - self.test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        return X_train, X_test, y_train, y_test
