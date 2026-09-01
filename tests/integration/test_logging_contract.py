"""What a request writes to the log, and what it must never write."""
import json

import pytest
import structlog

from fraud_service.logging_setup import configure_logging

pytestmark = pytest.mark.integration

SENSITIVE_VALUES = ["CUST-0042", "412.5", "customer_id", "amount_sar"]


@pytest.fixture
def logged(client, valid_payload, capsys):
    configure_logging("INFO")
    client.post("/v1/predict", json=valid_payload)
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]
    structlog.reset_defaults()
    return lines


def test_a_prediction_emits_a_scoring_event(logged):
    events = [line for line in logged if line["event"] == "prediction_served"]
    assert len(events) == 1
    assert events[0]["decision"] == "allow"
    assert events[0]["model_version"] == "v-test"


def test_the_probability_is_bucketed_not_raw(logged):
    bucket = next(line for line in logged if line["event"] == "prediction_served")
    assert bucket["probability_bucket"] == 0.4      # 0.42 rounded to 0.1 steps
    assert "probability" not in bucket


def test_the_request_event_carries_status_and_latency(logged):
    request = next(line for line in logged if line["event"] == "http_request")
    assert request["status"] == 200
    assert request["path"] == "/v1/predict"
    assert isinstance(request["latency_ms"], float)


def test_both_events_share_one_trace_id(logged):
    ids = {line["trace_id"] for line in logged if "trace_id" in line}
    assert len(ids) == 1


def test_no_customer_data_reaches_the_log(logged):
    blob = json.dumps(logged)
    for value in SENSITIVE_VALUES:
        assert value not in blob, f"{value} leaked into the log stream"
