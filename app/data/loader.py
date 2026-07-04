"""
Provides robust I/O abstractions for data ingestion.

Strictly focuses on locating and safely reading external raw datasets into 
Pandas DataFrames without performing validation or preprocessing.
"""
import os
import pandas as pd
from typing import Protocol

from app.config import settings
from app.utils.logger import get_logger
from app.data.exceptions import DataLoaderError

logger = get_logger(__name__)

class DataLoaderProtocol(Protocol):
    """
    Protocol defining the strict interface for all data loaders.
    Ensures future extensions (e.g., S3DataLoader) share the exact same API.
    """
    def load(self, file_name: str) -> pd.DataFrame:
        """
        Loads raw data into a DataFrame.
        
        Args:
            file_name: Identifier for the data source.
            
        Returns:
            A raw Pandas DataFrame.
        """
        ...

class CSVDataLoader:
    """
    Loads raw data from local CSV files into Pandas DataFrames.
    """
    
    def __init__(self, data_dir: str = settings.data_dir):
        """
        Args:
            data_dir: The root directory where CSV files are stored.
        """
        self.data_dir = data_dir

    def load(self, file_name: str) -> pd.DataFrame:
        """
        Safely loads a CSV file from the configured data directory.
        
        Args:
            file_name: Name of the CSV file including extension.
            
        Returns:
            A Pandas DataFrame containing the raw, unvalidated data.
            
        Raises:
            DataLoaderError: If the file does not exist, lacks read permissions,
                             or fails to parse as a CSV.
        """
        if not file_name or not file_name.strip():
            raise DataLoaderError("Provided file name cannot be empty.")

        file_path = os.path.join(self.data_dir, file_name)
        
        if not os.path.exists(file_path):
            error_msg = f"Data file not found at path: {file_path}"
            logger.error(error_msg)
            raise DataLoaderError(error_msg)
            
        try:
            logger.info(f"Loading CSV data from: {file_path}")
            df = pd.read_csv(file_path)
            logger.info(f"Successfully loaded {len(df)} rows and {len(df.columns)} columns from {file_name}.")
            return df
        except Exception as e:
            error_msg = f"Failed to parse CSV file '{file_path}': {e}"
            logger.error(error_msg)
            raise DataLoaderError(error_msg) from e
