"""The decision bands. With block_threshold=0.85 and REVIEW_BAND=0.15 the
boundaries sit at 0.70 and 0.85, and both are inclusive-lower."""
import pytest

from fraud_service.domain.entities import Decision
from fraud_service.domain.policies import REVIEW_BAND, decide

THRESHOLD = 0.85


@pytest.mark.unit
@pytest.mark.parametrize("probability,expected", [
    (0.0, Decision.ALLOW),
    (0.4999, Decision.ALLOW),
    (0.6999, Decision.ALLOW),
    (0.70, Decision.REVIEW),
    (0.8499, Decision.REVIEW),
    (0.85, Decision.BLOCK),
    (0.99, Decision.BLOCK),
    (1.0, Decision.BLOCK),
])
def test_decision_bands(probability: float, expected: Decision) -> None:
    assert decide(probability, THRESHOLD) is expected


@pytest.mark.unit
def test_block_boundary_is_inclusive() -> None:
    assert decide(THRESHOLD, THRESHOLD) is Decision.BLOCK


@pytest.mark.unit
def test_review_boundary_is_inclusive() -> None:
    assert decide(THRESHOLD - REVIEW_BAND, THRESHOLD) is Decision.REVIEW


@pytest.mark.unit
def test_just_below_review_boundary_allows() -> None:
    assert decide(THRESHOLD - REVIEW_BAND - 1e-9, THRESHOLD) is Decision.ALLOW


@pytest.mark.unit
@pytest.mark.parametrize("threshold", [0.5, 0.7, 0.95])
def test_threshold_is_configurable(threshold: float) -> None:
    assert decide(threshold, threshold) is Decision.BLOCK
    assert decide(threshold - REVIEW_BAND, threshold) is Decision.REVIEW
    assert decide(threshold - REVIEW_BAND - 0.01, threshold) is Decision.ALLOW
