from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from fraud_service.api.schemas import HealthResponse, PredictRequest, PredictResponse, ReadyResponse
from fraud_service.service.scorer import FraudScorer

router = APIRouter(tags=["fraud"])


def get_scorer(request: Request) -> FraudScorer:
    """DI seam: Lab 4's tests override this one function to inject a fake
    model - no real sklearn artefact needed to test the API contract."""
    scorer: FraudScorer | None = getattr(request.app.state, "scorer", None)
    if scorer is None:                       # startup incomplete/failed
        raise HTTPException(status_code=503, detail="Model not ready",
                            headers={"Retry-After": "5"})
    return scorer


# NOT async def - sklearn inference is CPU-bound. FastAPI runs plain `def`
# routes in a thread pool automatically; `async def` here would run the
# CPU-bound call directly on the single event loop and block every other
# in-flight request until it finishes.
@router.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest, request: Request,
            scorer: Annotated[FraudScorer, Depends(get_scorer)]) -> PredictResponse:
    score = scorer.score(body.to_domain())
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


# The dependency is required for its effect, not its value: get_scorer raises
# 503 when the model is not wired. Declared here rather than as an unused
# parameter, so the signature says what the handler actually uses.
@router.get("/ready", response_model=ReadyResponse, dependencies=[Depends(get_scorer)])
def ready() -> ReadyResponse:
    """Readiness: can I serve correctly RIGHT NOW?

    Deliberately the same dependency /predict resolves, not a second look at
    app.state - readiness that checks a different thing from the one the hot
    path needs is readiness that can lie."""
    return ReadyResponse(status="ready")
