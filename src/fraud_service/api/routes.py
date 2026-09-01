from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from fraud_service.api.schemas import HealthResponse, PredictRequest, PredictResponse, ReadyResponse
from fraud_service.service.scorer import FraudScorer

router = APIRouter(tags=["fraud"])
log = structlog.get_logger()


def get_scorer(request: Request) -> FraudScorer:
    """The seam tests override to inject a fake model."""
    scorer: FraudScorer | None = getattr(request.app.state, "scorer", None)
    if scorer is None:                       # startup incomplete/failed
        raise HTTPException(status_code=503, detail="Model not ready",
                            headers={"Retry-After": "5"})
    return scorer


# Not async: sklearn inference is CPU-bound, and FastAPI runs plain `def`
# routes in a threadpool. As `async def` it would block the event loop.
@router.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest, request: Request,
            scorer: Annotated[FraudScorer, Depends(get_scorer)]) -> PredictResponse:
    score = scorer.score(body.to_domain())
    # Bucketed, and no customer_id or amount: a raw score beside an identifier
    # is personal data under PDPL.
    log.info("prediction_served", decision=score.decision.value,
             probability_bucket=round(score.probability, 1),
             model_version=score.model_version)
    return PredictResponse(
        transaction_id=score.transaction_id,
        fraud_probability=round(score.probability, 6),
        decision=score.decision,
        model_version=score.model_version,
        trace_id=request.state.trace_id,
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: is the process alive? NO I/O here - ever."""
    return HealthResponse(status="ok")


# Declared as a dependency, not a parameter: needed for its 503, not its value.
@router.get("/ready", response_model=ReadyResponse, dependencies=[Depends(get_scorer)])
def ready() -> ReadyResponse:
    """Readiness resolves the same dependency /predict does, so it cannot lie."""
    return ReadyResponse(status="ready")
