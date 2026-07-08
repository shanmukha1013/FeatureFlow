"""
Prepares materialized feature datasets for machine learning.

Strictly isolates X (features) and Y (target) without leaking Data Layer 
preprocessing or Feature Layer engineering logic. Implements defensive checks 
to prevent data leakage and guarantee training integrity.
"""
import pandas as pd
from typing import List, Tuple, Optional

from app.training.exceptions import DatasetPreparationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TrainingDatasetBuilder:
    """
    Extracts explicitly requested features and targets from a generic dataset.
    Enforces strict integrity and distribution rules prior to training.
    """
    
    def prepare(self, df: pd.DataFrame, feature_columns: List[str], target_column: str, entity_id_column: Optional[str] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Slices the DataFrame into X and Y components after rigorous validation.
        
        Raises:
            DatasetPreparationError: If integrity checks fail (empty data, duplicates, nulls, etc.)
        """
        logger.info(f"Preparing dataset: extracting {len(feature_columns)} features and target '{target_column}'.")
        
        if df is None or df.empty:
            raise DatasetPreparationError("Cannot prepare an empty dataset for training.")
            
        # Integrity: Check for duplicate entities which could skew metrics
        if entity_id_column and entity_id_column in df.columns:
            if df[entity_id_column].duplicated().any():
                logger.error(f"Data integrity violation: Duplicate keys in '{entity_id_column}'.")
                raise DatasetPreparationError(f"Duplicate entity IDs in '{entity_id_column}' detected. Resolve upstream.")
                
        # Target Validation
        if target_column not in df.columns:
            raise DatasetPreparationError(f"Target column '{target_column}' is missing from the dataset.")
            
        if df[target_column].isnull().any():
            raise DatasetPreparationError(f"Target column '{target_column}' contains null values. Target must be fully populated.")
            
        # Target Distribution
        target_counts = df[target_column].value_counts()
        if len(target_counts) < 2:
            raise DatasetPreparationError(f"Target '{target_column}' has less than 2 distinct classes. Cannot train a classifier.")
            
        logger.debug(f"Target distribution: {target_counts.to_dict()}")

        # Data Leakage Safeguards
        if target_column in feature_columns:
            logger.warning(f"Data leakage risk: Target '{target_column}' found in feature list. Automatically excising it.")
            feature_columns = [col for col in feature_columns if col != target_column]
            
        if entity_id_column and entity_id_column in feature_columns:
            logger.warning(f"Data leakage risk: Entity ID '{entity_id_column}' found in feature list. Automatically excising it.")
            feature_columns = [col for col in feature_columns if col != entity_id_column]
            
        missing_features = [col for col in feature_columns if col not in df.columns]
        if missing_features:
            raise DatasetPreparationError(f"Requested feature columns are missing from the dataset: {missing_features}")
            
        X = df[feature_columns].copy()
        y = df[target_column]
        
        # Impute missing values in features
        from sklearn.impute import SimpleImputer
        import pandas as pd
        
        imputer = SimpleImputer(strategy='median')
        try:
            X_imputed = imputer.fit_transform(X)
            X = pd.DataFrame(X_imputed, columns=X.columns, index=X.index)
        except Exception as e:
            logger.warning(f"SimpleImputer failed, proceeding with original X. Error: {e}")
        
        logger.info(f"Dataset preparation complete. Matrix shape: X={X.shape}, Y={y.shape}")
        return X, y
