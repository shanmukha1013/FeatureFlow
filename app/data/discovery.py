"""
Automatically discovers and maps datasets from the local file system.

Ensures that FeatureFlow can seamlessly ingest new data sources dynamically
by matching files in the configured directory against the Schema Registry.
"""
import os
import glob
from typing import Dict

from app.config import settings
from app.utils.logger import get_logger
from app.data.schema import SchemaRegistry

logger = get_logger(__name__)

class DatasetDiscovery:
    """
    Automatically discovers datasets from the configured data directory.
    Matches discovered files to registered schemas based on filename conventions.
    """
    def __init__(self, registry: SchemaRegistry, data_dir: str = settings.data_dir) -> None:
        self.registry = registry
        self.data_dir = data_dir

    def discover_datasets(self) -> Dict[str, str]:
        """
        Scans the data directory for .csv files.
        Returns a mapping of dataset_name (schema name) to file_name.
        """
        logger.info(f"Initiating automatic dataset discovery in '{self.data_dir}'.")
        
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory '{self.data_dir}' does not exist.")
            return {}

        discovered: Dict[str, str] = {}
        # Convention: file basename (without .csv) corresponds to the registered schema name
        for file_path in glob.glob(os.path.join(self.data_dir, "*.csv")):
            file_name = os.path.basename(file_path)
            dataset_name = os.path.splitext(file_name)[0]
            
            if self.registry.has_schema(dataset_name):
                discovered[dataset_name] = file_name
                logger.info(f"Discovered supported dataset: '{dataset_name}' -> '{file_name}'")
            else:
                logger.debug(f"Ignored '{file_name}': No registered schema for '{dataset_name}'")
                
        logger.info(f"Discovery complete. Found {len(discovered)} supported datasets.")
        return discovered
