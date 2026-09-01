"""Fixtures for the whole suite. Helpers live in tests/support.py."""
import pytest
from fastapi.testclient import TestClient

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.api.app import create_app
from fraud_service.api.routes import get_scorer
from fraud_service.service.scorer import FraudScorer
from tests.support import BLOCK_THRESHOLD, MODEL_PATH, StubModel


@pytest.fixture
def stub_model() -> StubModel:
    return StubModel()


@pytest.fixture
def client(stub_model: StubModel) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_scorer] = lambda: FraudScorer(
        model=stub_model, block_threshold=BLOCK_THRESHOLD)
    # Not `with TestClient(...)`: that runs lifespan, which loads the real artefact.
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
    """The real artefact, loaded once per session."""
    if not MODEL_PATH.exists():
        pytest.skip(f"model artefact missing at {MODEL_PATH}")
    return SklearnModel.load(MODEL_PATH)


@pytest.fixture(scope="session")
def real_scorer(real_model: SklearnModel) -> FraudScorer:
    return FraudScorer(model=real_model, block_threshold=BLOCK_THRESHOLD)
