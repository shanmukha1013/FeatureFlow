"""
Implements the core prediction endpoint.
"""
from fastapi import APIRouter, Request, BackgroundTasks
from app.serving.schemas.request import PredictRequestSchema
from app.serving.schemas.response import PredictResponseSchema
from app.serving.dependencies import get_prediction_engine
from app.inference.engine import PredictionEngine

router = APIRouter()


@router.post("/predict", response_model=PredictResponseSchema)
async def predict(
    payload: PredictRequestSchema,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Executes a machine learning prediction against the requested model alias.
    """
    engine: PredictionEngine = get_prediction_engine()

    req_id = getattr(request.state, "request_id", None)

    # 3. Predict via engine (engine handles the alias and Fallback mechanisms)
    domain_res = await engine.predict_single(
        features=payload.features,
        entity_id=payload.entity_id,
        alias=payload.alias,
        explain=payload.explain,
        background_tasks=background_tasks,
        user_id=getattr(request.state, "user", {}).get("id") if hasattr(request.state, "user") else None
    )

    # 5. Response mapping: Map back to the HTTP Pydantic contract
    return PredictResponseSchema(
        request_id=domain_res.request_id or req_id or "local",
        prediction=domain_res.prediction,
        probability=domain_res.probability,
        model_id=domain_res.model_name,
        model_version=domain_res.model_version,
        latency_ms=domain_res.latency_ms,
        warnings=domain_res.warnings,
        explanation=domain_res.explanation
    )


@router.post("/predict/explain", response_model=PredictResponseSchema)
async def predict_explain(
    payload: PredictRequestSchema,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Executes a prediction and guarantees explainability metadata is included.
    (Forces explain=True).
    """
    payload.explain = True
    return await predict(payload, request, background_tasks)
