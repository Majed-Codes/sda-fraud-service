from dataclasses import dataclass

from fraud_service.domain.entities import Decision, Transaction
from fraud_service.domain.policies import decide
from fraud_service.service.interfaces import Model


@dataclass(frozen=True)
class Score:
    transaction_id: str
    probability: float
    decision: Decision
    model_version: str


@dataclass
class FraudScorer:
    model: Model
    block_threshold: float

    def score(self, txn: Transaction) -> Score:
        features = txn.to_features()
        probability = self.model.predict_proba(features)
        return Score(
            transaction_id=txn.transaction_id,
            probability=probability,
            decision=decide(probability, self.block_threshold),
            model_version=self.model.model_version,
        )
