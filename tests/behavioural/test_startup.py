"""Lifespan for real: load the artefact, warm it, wire the scorer.

Nothing else in the suite runs lifespan, so without this it is unasserted.
"""
import pytest
from fastapi.testclient import TestClient

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.api.app import create_app
from fraud_service.service.scorer import FraudScorer

pytestmark = pytest.mark.behavioural


def test_lifespan_loads_warms_and_wires_the_real_model(monkeypatch, valid_payload):
    calls: list[str] = []
    original = SklearnModel.predict_proba

    def counting_predict_proba(self, features):
        calls.append("predict")
        return original(self, features)

    monkeypatch.setattr(SklearnModel, "predict_proba", counting_predict_proba)

    app = create_app()
    assert getattr(app.state, "scorer", None) is None

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/v1/ready").status_code == 503

    with client:
        # Warm-up ran during startup, before any request arrived.
        assert calls == ["predict"], "startup did not warm the model"

        scorer = app.state.scorer
        assert isinstance(scorer, FraudScorer)
        assert scorer.block_threshold == 0.85
        assert scorer.model.model_version == "v3.2.0"

        assert client.get("/v1/ready").status_code == 200

        body = client.post("/v1/predict", json=valid_payload).json()
        assert body["model_version"] == "v3.2.0"
        assert body["fraud_probability"] == 0.557066
        assert body["decision"] == "allow"
        assert len(calls) == 2

    # Shut down: liveness must still answer, readiness must not.
    assert client.get("/v1/health").status_code == 200
