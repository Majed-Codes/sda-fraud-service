"""Shared helpers. Kept out of conftest.py, which only resolves under pytest."""
from datetime import UTC, datetime
from pathlib import Path

from fraud_service.domain.entities import FeatureVector, Transaction

MODEL_PATH = Path("models/fraud_xgb_v3.joblib")
STUB_PROBABILITY = 0.42
BLOCK_THRESHOLD = 0.85


class StubModel:
    """Satisfies the Model protocol by shape alone, and records its calls."""

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
