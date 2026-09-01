"""Shared test helpers.

Deliberately not in conftest.py. conftest is a pytest plugin module that the
framework collects by path - importing from it only resolves while pytest is
driving, so editors, linters and a plain `python -c` all fail on it. Helpers
that tests import belong in an ordinary module; conftest keeps the fixtures.
"""
from datetime import UTC, datetime
from pathlib import Path

from fraud_service.domain.entities import FeatureVector, Transaction

MODEL_PATH = Path("models/fraud_xgb_v3.joblib")
STUB_PROBABILITY = 0.42
BLOCK_THRESHOLD = 0.85


class StubModel:
    """Satisfies the Model protocol by shape alone - no inheritance, no sklearn.

    Records what it was asked to score so tests can assert on the features the
    API actually derived from the request.
    """

    def __init__(self, probability: float = STUB_PROBABILITY,
                 model_version: str = "v-test") -> None:
        self.probability = probability
        self.model_version = model_version
        self.calls: list[FeatureVector] = []

    def predict_proba(self, features: FeatureVector) -> float:
        self.calls.append(features)
        return self.probability


def make_transaction(**overrides) -> Transaction:
    fields = {
        "transaction_id": "TXN-2026-00042",
        "amount_sar": 412.5,
        "channel": "ecom",
        "merchant_category": "ELECTRONICS",
        "customer_id": "CUST-0042",
        "timestamp": datetime(2026, 7, 5, 22, 14, tzinfo=UTC),
    }
    fields.update(overrides)
    return Transaction(**fields)
