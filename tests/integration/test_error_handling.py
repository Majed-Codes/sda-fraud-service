"""An unhandled exception must reach the client as an envelope and a trace
id - never a traceback, a module path, or an internal message."""
import pytest
from fastapi.testclient import TestClient

from fraud_service.api.app import create_app
from fraud_service.api.routes import get_scorer
from fraud_service.service.scorer import FraudScorer
from tests.conftest import BLOCK_THRESHOLD, StubModel

pytestmark = pytest.mark.integration

SECRET = "connection string postgres://user:hunter2@prod-db:5432"


class ExplodingModel(StubModel):
    def predict_proba(self, features):
        raise RuntimeError(f"model backend unreachable: {SECRET}")


@pytest.fixture
def exploding_client() -> TestClient:
    """raise_server_exceptions=False makes TestClient behave like a real
    server: return the handler's 500 instead of re-raising into the test."""
    app = create_app()
    app.dependency_overrides[get_scorer] = lambda: FraudScorer(
        model=ExplodingModel(), block_threshold=BLOCK_THRESHOLD)
    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_returns_the_error_envelope(exploding_client, valid_payload):
    response = exploding_client.post("/v1/predict", json=valid_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == {"code": "internal_error", "message": "Internal server error"}
    assert len(body["trace_id"]) == 16


def test_unhandled_exception_leaks_nothing(exploding_client, valid_payload):
    text = exploding_client.post("/v1/predict", json=valid_payload).text

    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert SECRET not in text
    assert "hunter2" not in text
    assert "fraud_service" not in text


def test_the_trace_id_is_logged_with_the_traceback(exploding_client, valid_payload, caplog):
    # The detail has to survive somewhere - it goes to the log, keyed by the
    # same id the client was handed, or the trace id buys the operator nothing.
    with caplog.at_level("ERROR"):
        response = exploding_client.post("/v1/predict", json=valid_payload)

    trace_id = response.json()["trace_id"]
    assert any(trace_id in record.getMessage() for record in caplog.records)
    assert any(record.exc_info for record in caplog.records)


def test_unknown_route_returns_the_envelope_too(client):
    response = client.get("/v1/does-not-exist")

    assert response.status_code == 404
    assert set(response.json()) == {"error", "trace_id"}


def test_ready_returns_503_before_the_model_is_loaded(valid_payload):
    # No dependency override and no lifespan: app.state.scorer is absent,
    # which is exactly the state an orchestrator probes during a rollout.
    client = TestClient(create_app(), raise_server_exceptions=False)

    ready = client.get("/v1/ready")
    assert ready.status_code == 503
    assert ready.json()["error"]["code"] == "not_ready"

    predict = client.post("/v1/predict", json=valid_payload)
    assert predict.status_code == 503
    assert predict.headers["Retry-After"] == "5"


def test_health_stays_up_while_the_model_is_missing():
    # Liveness must not fail just because readiness does, or the orchestrator
    # restarts a process that is loading perfectly well.
    client = TestClient(create_app(), raise_server_exceptions=False)
    assert client.get("/v1/health").status_code == 200
