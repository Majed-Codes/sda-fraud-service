"""Every failure leaves through here in one envelope, carrying the trace id."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Starlette's, not FastAPI's subclass: the router raises the base class for 404.
from starlette.exceptions import HTTPException

from fraud_service.api.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

CODES = {400: "bad_request", 404: "not_found", 422: "validation_error", 503: "not_ready"}


def _envelope(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    body = ErrorResponse(error=ErrorDetail(code=code, message=message), trace_id=trace_id)
    return JSONResponse(status_code=status_code, content=body.model_dump(),
                        headers={"X-Trace-Id": trace_id})


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _envelope(request, 422, "validation_error", _summarise(exc))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        response = _envelope(request, exc.status_code,
                             CODES.get(exc.status_code, "http_error"), str(exc.detail))
        for key, value in (exc.headers or {}).items():
            response.headers[key] = value
        return response

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, _exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error trace_id=%s path=%s",
                         getattr(request.state, "trace_id", "unavailable"),
                         request.url.path)
        return _envelope(request, 500, "internal_error", "Internal server error")


def _summarise(exc: RequestValidationError) -> str:
    fields = set()
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        fields.add(location or "body")
    return f"Request validation failed for: {', '.join(sorted(fields))}"
