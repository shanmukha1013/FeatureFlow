"""
Validates prediction requests before execution.
"""
import pandas as pd
from typing import List

from app.inference.base import BaseInferenceValidator
from app.inference.request import PredictionRequest
from app.inference.exceptions import InputValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RequestValidator(BaseInferenceValidator):
    """
    Ensures that incoming inference requests strictly adhere to the exact 
    feature signature used during training. Protects predictors from silent failures.
    """
    
    def validate(self, request: PredictionRequest, expected_features: List[str]) -> List[str]:
        warnings = []
        
        if not expected_features:
            raise InputValidationError("Cannot validate request: The model metadata lacks expected feature definitions.")
            
        if not request.features:
            raise InputValidationError(f"PredictionRequest '{request.request_id}' contains an empty feature vector.")
            
        # 1. Verify missing required features
        missing_features = [f for f in expected_features if f not in request.features]
        if missing_features:
            raise InputValidationError(f"Missing required features for inference: {missing_features}")
            
        # 2. Prevent nulls and strictly invalid types which crash numerical algorithms
        for f in expected_features:
            val = request.features.get(f)
            
            if pd.isna(val):
                raise InputValidationError(f"Feature '{f}' contains NaN or Null. Inference models require fully populated vectors.")
                
            if isinstance(val, (list, dict)):
                raise InputValidationError(f"Feature '{f}' has invalid complex type {type(val)}. Expected scalar value.")
                
        # 3. Track unexpected extra features (Log as warnings, do not fail)
        extra = [f for f in request.features if f not in expected_features]
        if extra:
            # Only truncate log output to avoid massive logs if a huge dict is passed
            warning_msg = f"Request contains {len(extra)} unexpected features that will be safely ignored (e.g. {extra[:3]})."
            logger.warning(warning_msg)
            warnings.append(warning_msg)
            
        return warnings
