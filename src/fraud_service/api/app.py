"""The composition root for the API - same idea as batch.py's main(),
now for the HTTP entrypoint. The model loads ONCE, here, in lifespan -
never at import time, never per-request."""
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC
from pathlib import Path

from fastapi import FastAPI, Request

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.api.errors import install_error_handlers
from fraud_service.api.routes import router
from fraud_service.service.scorer import FraudScorer


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    model = SklearnModel.load(Path("models/fraud_xgb_v3.joblib"))
    # Warm-up: pay the lazy-init cost now, not on the first real user request.
    model.predict_proba(_warmup_features())
    print(f"model_loaded version={model.model_version} "
          f"seconds={time.perf_counter() - t0:.3f}")

    app.state.scorer = FraudScorer(model=model, block_threshold=0.85)
    yield
    print("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(title="Fraud Scoring Service", lifespan=lifespan)
    app.include_router(router, prefix="/v1")
    install_error_handlers(app)

    @app.middleware("http")
    async def trace_and_time(request: Request, call_next):
        trace_id = uuid.uuid4().hex[:16]
        request.state.trace_id = trace_id
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(
            round((time.perf_counter() - t0) * 1000, 1))
        return response

    return app


def _warmup_features():
    from datetime import datetime

    from fraud_service.domain.entities import Transaction
    return Transaction(
        transaction_id="WARMUP-0000", amount_sar=100.0, channel="pos",
        merchant_category="GROCERY", customer_id="warmup",
        timestamp=datetime.now(UTC)).to_features()


app = create_app()
