"""The full HTTP contract for a valid request: status, envelope, headers."""
import pytest

from tests.conftest import STUB_PROBABILITY

pytestmark = pytest.mark.integration


def test_valid_request_returns_the_documented_envelope(client, valid_payload, stub_model):
    response = client.post("/v1/predict", json=valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"transaction_id", "fraud_probability", "decision",
                         "model_version", "trace_id"}
    assert body["transaction_id"] == valid_payload["transaction_id"]
    assert body["fraud_probability"] == pytest.approx(STUB_PROBABILITY)
    assert body["decision"] == "allow"
    assert body["model_version"] == stub_model.model_version


def test_response_carries_trace_and_timing_headers(client, valid_payload):
    response = client.post("/v1/predict", json=valid_payload)

    trace_id = response.headers["X-Trace-Id"]
    assert len(trace_id) == 16
    assert response.json()["trace_id"] == trace_id
    assert float(response.headers["X-Response-Time-Ms"]) >= 0


def test_trace_id_is_unique_per_request(client, valid_payload):
    ids = {client.post("/v1/predict", json=valid_payload).json()["trace_id"]
           for _ in range(10)}
    assert len(ids) == 10


def test_probability_is_rounded_to_six_places(client, valid_payload, stub_model):
    stub_model.probability = 0.5570662261643815
    body = client.post("/v1/predict", json=valid_payload).json()
    assert body["fraud_probability"] == 0.557066


@pytest.mark.parametrize("probability,expected", [
    (0.10, "allow"), (0.70, "review"), (0.85, "block"), (0.99, "block"),
])
def test_decision_reflects_the_score(client, valid_payload, stub_model,
                                     probability, expected):
    stub_model.probability = probability
    assert client.post("/v1/predict", json=valid_payload).json()["decision"] == expected


def test_request_reaches_the_model_as_normalised_features(client, valid_payload, stub_model):
    valid_payload["merchant_category"] = "home goods"
    client.post("/v1/predict", json=valid_payload)

    assert len(stub_model.calls) == 1
    features = stub_model.calls[0].values
    assert features["mcc"] == "HOME_GOODS"
    assert features["channel"] == "ecom"
    assert features["hour_of_day"] == 22
    assert features["is_night"] == 0


def test_health_is_always_ok(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_ready_once_the_scorer_exists(client):
    response = client.get("/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
