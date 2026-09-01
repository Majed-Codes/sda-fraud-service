"""Composition root for the API. The model loads once, here, in lifespan."""
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import structlog
from fastapi import FastAPI, Request, Response

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.api.errors import install_error_handlers
from fraud_service.api.routes import router
from fraud_service.config import Settings
from fraud_service.domain.entities import Channel, FeatureVector, Transaction
from fraud_service.logging_setup import configure_logging
from fraud_service.service.scorer import FraudScorer

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    # Again, not only in create_app: uvicorn installs its own handlers after
    # importing the app, which undoes the configuration done at import time.
    configure_logging(settings.log_level, json=settings.log_json)
    started = time.perf_counter()
    model = SklearnModel.load(settings.model_path)
    # Pay the lazy-init cost now, not on the first real request.
    model.predict_proba(_warmup_features())
    app.state.scorer = FraudScorer(model=model,
                                   block_threshold=settings.block_threshold)
    log.info("model_loaded", model_version=model.model_version,
             seconds=round(time.perf_counter() - started, 3),
             git_sha=settings.git_sha)
    yield
    log.info("shutdown_complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    # Settings() raises here, at startup, rather than on the first request.
    settings = settings or Settings()
    configure_logging(settings.log_level, json=settings.log_json)

    app = FastAPI(title="Fraud Scoring Service", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router, prefix="/v1")
    install_error_handlers(app)

    @app.middleware("http")
    async def trace_and_time(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = uuid.uuid4().hex[:16]
        request.state.trace_id = trace_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id, path=request.url.path, method=request.method,
            git_sha=settings.git_sha)

        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)

        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(latency_ms)
        log.info("http_request", status=response.status_code, latency_ms=latency_ms)
        return response

    return app


def _warmup_features() -> FeatureVector:
    return Transaction(
        transaction_id="WARMUP-0000", amount_sar=100.0, channel=Channel.POS,
        merchant_category="GROCERY", customer_id="warmup",
        timestamp=datetime.now(UTC)).to_features()


app = create_app()
