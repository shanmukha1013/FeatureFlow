"""
Implements the core prediction endpoint.
"""
from fastapi import APIRouter, Request
from app.serving.schemas.request import PredictRequestSchema
from app.serving.schemas.response import PredictResponseSchema
from app.serving.dependencies import get_prediction_engine
from app.inference.engine import PredictionEngine

router = APIRouter()

# Note: Standard `def` (not `async def`) is intentionally used here.
# ML inference operations (scikit-learn .predict()) are synchronous and CPU-bound.
# Using standard `def` allows FastAPI to safely offload execution to a background 
# threadpool, preventing the asynchronous event loop from blocking.
@router.post("/predict", response_model=PredictResponseSchema)
async def predict(
    payload: PredictRequestSchema, 
    request: Request
):
    """
    Executes a machine learning prediction against the requested model alias.
    """
    engine: PredictionEngine = get_prediction_engine()
    
    # 2. Extract correlation ID set by middleware
    req_id = getattr(request.state, "request_id", None)
    
    # 3. Predict via engine (engine handles the alias and Fallback mechanisms)
    domain_res = await engine.predict_single(features=payload.features, entity_id=payload.entity_id, alias=payload.alias)
    
    # 5. Response mapping: Map back to the HTTP Pydantic contract
    return PredictResponseSchema(
        request_id=domain_res.request_id or req_id or "local",
        prediction=domain_res.prediction,
        probability=domain_res.probability,
        model_id=domain_res.model_id,
        model_version=domain_res.model_version,
    )

@router.post("/predict/explain", response_model=PredictResponseSchema)
async def predict_explain(
    payload: PredictRequestSchema, 
    request: Request
):
    """
    Executes a prediction and guarantees explainability metadata is included.
    (This is identical to /predict now since explanations are strictly enabled by default).
    """
    return await predict(payload, request)
