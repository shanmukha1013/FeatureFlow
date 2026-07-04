"""
Implements the core prediction endpoint.
"""
from fastapi import APIRouter, Depends, Request
from app.serving.schemas.request import PredictRequestSchema
from app.serving.schemas.response import PredictResponseSchema
from app.serving.dependencies import get_cached_predictor
from app.inference.request import PredictionRequest
from app.inference.predictor import ModelPredictor

router = APIRouter()

# Note: Standard `def` (not `async def`) is intentionally used here.
# ML inference operations (scikit-learn .predict()) are synchronous and CPU-bound.
# Using standard `def` allows FastAPI to safely offload execution to a background 
# threadpool, preventing the asynchronous event loop from blocking.
@router.post("/predict", response_model=PredictResponseSchema)
def predict(
    payload: PredictRequestSchema, 
    request: Request
):
    """
    Executes a machine learning prediction against the requested model alias.
    """
    # 1. We resolve the cache predictor via an explicit call rather than a Depends 
    # to allow dynamic passing of the alias parameter.
    predictor: ModelPredictor = get_cached_predictor(payload.alias)
    
    # 2. Extract correlation ID set by middleware
    req_id = getattr(request.state, "request_id", None)
    
    # 3. Domain mapping: Map the HTTP Pydantic contract to the internal Inference Layer contract
    domain_req = PredictionRequest(
        entity_id=payload.entity_id,
        features=payload.features,
        request_id=req_id
    )
    
    # 4. Predict
    domain_res = predictor.predict(domain_req)
    
    # 5. Response mapping: Map back to the HTTP Pydantic contract
    return PredictResponseSchema(
        request_id=domain_res.request_id,
        prediction=domain_res.prediction,
        probability=domain_res.probability,
        model_id=domain_res.model_id,
        model_version=domain_res.model_version,
        latency_ms=domain_res.latency_ms,
        warnings=domain_res.warnings
    )
