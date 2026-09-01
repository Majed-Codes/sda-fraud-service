"""Training/serving skew guard against the recorded v3 scores.

The full 5000-row sweep is marked slow; a head sample runs per-commit.
"""
import csv
from pathlib import Path

import pytest

from fraud_service.domain.entities import Transaction

pytestmark = pytest.mark.behavioural

GOLDEN_PATH = Path("data/golden_scores_v3.csv")
TOLERANCE = 1e-9
SAMPLE_SIZE = 250


def _load_golden() -> list[dict]:
    if not GOLDEN_PATH.exists():
        pytest.skip(f"golden file missing at {GOLDEN_PATH}")
    with GOLDEN_PATH.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _rescore(scorer, row: dict) -> float:
    # The `mcc` column is already normalised, so to_features must be a no-op here.
    return scorer.score(Transaction(
        transaction_id=row["transaction_id"],
        amount_sar=float(row["amount_sar"]),
        channel=row["channel"],
        merchant_category=row["mcc"],
        customer_id=row["customer_id"],
        timestamp=row["timestamp"],
    )).probability


def _worst_drift(scorer, rows: list[dict]) -> tuple[float, str]:
    worst, worst_id = 0.0, ""
    for row in rows:
        drift = abs(_rescore(scorer, row) - float(row["score"]))
        if drift > worst:
            worst, worst_id = drift, row["transaction_id"]
    return worst, worst_id


def test_golden_file_is_populated():
    rows = _load_golden()
    assert len(rows) == 5000
    assert {"transaction_id", "amount_sar", "channel", "mcc",
            "customer_id", "timestamp", "score"} <= set(rows[0])


def test_head_sample_matches_golden(real_scorer):
    worst, worst_id = _worst_drift(real_scorer, _load_golden()[:SAMPLE_SIZE])
    assert worst < TOLERANCE, f"{worst_id} drifted by {worst:.3e}"


@pytest.mark.slow
def test_every_golden_row_matches(real_scorer):
    worst, worst_id = _worst_drift(real_scorer, _load_golden())
    assert worst < TOLERANCE, f"{worst_id} drifted by {worst:.3e}"


@pytest.mark.slow
def test_golden_rows_survive_a_casing_round_trip(real_scorer):
    # Lower-cased on the way in; normalisation must land on the same score.
    rows = _load_golden()[:SAMPLE_SIZE]
    for row in rows:
        lowered = dict(row, mcc=row["mcc"].lower().replace("_", " "))
        assert _rescore(real_scorer, lowered) == pytest.approx(
            float(row["score"]), abs=TOLERANCE)
