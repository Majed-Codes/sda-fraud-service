"""JSON logs to stdout, correlated by trace id.

stdlib records go through the same pipeline, so uvicorn's own lines are JSON
too - one non-JSON line is enough to break a log query.

Masking is a safety net, not permission to log secrets.
"""
import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization",
                  "national_id", "card_number", "pan", "cvv", "iban"}
MASK = "***MASKED***"

UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi")
HANDLER_NAME = "fraud_json"


def _mask_sensitive(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event_dict):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = MASK
    return event_dict


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _mask_sensitive,
    ]
    renderer: Any = (structlog.processors.JSONRenderer() if json
                     else structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    renderer],
    ))

    # Replace only the handler this function owns. Assigning root.handlers would
    # evict foreign ones - pytest's caplog among them - and silence them.
    root = logging.getLogger()
    for existing in [h for h in root.handlers if h.get_name() == HANDLER_NAME]:
        root.removeHandler(existing)
    root.addHandler(handler)
    if root.level == logging.NOTSET or root.level > logging.getLevelNamesMapping()[level]:
        root.setLevel(level)
    for name in UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
