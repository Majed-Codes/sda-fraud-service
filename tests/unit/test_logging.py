"""Every line is JSON, correlated, and free of secrets."""
import json
import logging

import pytest
import structlog

from fraud_service.logging_setup import MASK, configure_logging

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_logging():
    yield
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()


def _emit(capsys, **fields) -> dict:
    configure_logging("INFO")
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id="t" * 16)
    structlog.get_logger().info("prediction_served", **fields)
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_output_is_one_json_object_per_line(capsys):
    line = _emit(capsys, decision="allow")
    assert line["event"] == "prediction_served"
    assert line["level"] == "info"
    assert line["decision"] == "allow"


def test_every_line_carries_the_bound_trace_id(capsys):
    assert _emit(capsys)["trace_id"] == "t" * 16


def test_timestamps_are_utc_iso(capsys):
    assert _emit(capsys)["timestamp"].endswith("Z")


@pytest.mark.parametrize("key", [
    "password", "token", "secret", "api_key", "authorization",
    "national_id", "card_number", "pan", "cvv", "iban",
])
def test_sensitive_keys_are_masked(capsys, key):
    assert _emit(capsys, **{key: "hunter2"})[key] == MASK


def test_masking_is_case_insensitive(capsys):
    assert _emit(capsys, Authorization="Bearer abc")["Authorization"] == MASK


def test_ordinary_fields_survive(capsys):
    line = _emit(capsys, decision="block", probability_bucket=0.9)
    assert line["decision"] == "block"
    assert line["probability_bucket"] == 0.9


def test_stdlib_records_render_as_json_too(capsys):
    # uvicorn logs through stdlib; one plain line breaks every log query.
    configure_logging("INFO")
    logging.getLogger("uvicorn.error").info("Started server process [1]")
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["event"]
