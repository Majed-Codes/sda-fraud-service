"""Every failure leaves through here, in one envelope, carrying the trace id.

An unhandled exception must never reach the client as a stack trace: the
traceback goes to the logs, the client gets a code and the trace id that
ties their report to those logs.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Starlette's HTTPException, not FastAPI's subclass: the router raises the
# base class for 404/405, so registering the subclass misses them.
from starlette.exceptions import HTTPException

from fraud_service.api.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


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
        response = _envelope(request, exc.status_code, _code_for(exc.status_code),
                             str(exc.detail))
        for key, value in (exc.headers or {}).items():
            response.headers[key] = value
        return response

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, _exc: Exception) -> JSONResponse:
        # exc_info goes to the logs; the client gets the trace id, nothing else.
        logger.exception("unhandled_error trace_id=%s path=%s",
                         getattr(request.state, "trace_id", "unavailable"),
                         request.url.path)
        return _envelope(request, 500, "internal_error", "Internal server error")


def _summarise(exc: RequestValidationError) -> str:
    fields = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        fields.append(location or "body")
    return f"Request validation failed for: {', '.join(sorted(set(fields)))}"


def _code_for(status_code: int) -> str:
    return {400: "bad_request", 404: "not_found", 422: "validation_error",
            503: "not_ready"}.get(status_code, "http_error")
