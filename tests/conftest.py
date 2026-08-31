"""Fixtures shared by the whole suite.

The API tests never touch sklearn. `get_scorer` is the seam the routes
depend on, so overriding that one function swaps the entire model out for
a stub - no artefact on disk, no pandas, no inference cost.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.api.app import create_app
from fraud_service.api.routes import get_scorer
from fraud_service.domain.entities import FeatureVector
from fraud_service.service.scorer import FraudScorer

MODEL_PATH = Path("models/fraud_xgb_v3.joblib")
STUB_PROBABILITY = 0.42
BLOCK_THRESHOLD = 0.85


class StubModel:
    """Satisfies the Model protocol by shape alone - no inheritance, no sklearn.

    Records what it was asked to score so tests can assert on the features
    the API actually derived from the request.
    """

    def __init__(self, probability: float = STUB_PROBABILITY,
                 model_version: str = "v-test") -> None:
        self.probability = probability
        self.model_version = model_version
        self.calls: list[FeatureVector] = []

    def predict_proba(self, features: FeatureVector) -> float:
        self.calls.append(features)
        return self.probability


@pytest.fixture
def stub_model() -> StubModel:
    return StubModel()


@pytest.fixture
def client(stub_model: StubModel) -> TestClient:
    """A TestClient whose scorer is the stub. lifespan is not run, so the
    real artefact is never loaded and startup cost never enters the suite."""
    app = create_app()
    app.dependency_overrides[get_scorer] = lambda: FraudScorer(
        model=stub_model, block_threshold=BLOCK_THRESHOLD)
    # Deliberately not `with TestClient(...)`: entering the context manager
    # runs lifespan, which loads the real artefact off disk. These tests are
    # about the HTTP contract, so the stub is the whole point.
    return TestClient(app)


@pytest.fixture
def valid_payload() -> dict:
    return {
        "transaction_id": "TXN-2026-00042",
        "amount_sar": 412.5,
        "channel": "ecom",
        "merchant_category": "ELECTRONICS",
        "customer_id": "CUST-0042",
        "timestamp": "2026-07-05T22:14:00Z",
    }


@pytest.fixture(scope="session")
def real_model() -> SklearnModel:
    """The actual artefact, loaded once for the whole session. Only the
    behavioural tests use this - everything else uses the stub."""
    if not MODEL_PATH.exists():
        pytest.skip(f"model artefact missing at {MODEL_PATH}")
    return SklearnModel.load(MODEL_PATH)


@pytest.fixture(scope="session")
def real_scorer(real_model: SklearnModel) -> FraudScorer:
    return FraudScorer(model=real_model, block_threshold=BLOCK_THRESHOLD)


def make_transaction(**overrides):
    from fraud_service.domain.entities import Transaction

    fields = {
        "transaction_id": "TXN-2026-00042",
        "amount_sar": 412.5,
        "channel": "ecom",
        "merchant_category": "ELECTRONICS",
        "customer_id": "CUST-0042",
        "timestamp": datetime(2026, 7, 5, 22, 14, tzinfo=timezone.utc),
    }
    fields.update(overrides)
    return Transaction(**fields)
