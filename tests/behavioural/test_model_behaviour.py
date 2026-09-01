"""Properties of the real artefact. These are the tests that catch a model
swap that is silently wrong - the stub cannot tell you anything here."""
from datetime import UTC, datetime

import pytest

from tests.support import make_transaction

pytestmark = pytest.mark.behavioural


@pytest.mark.parametrize("variant", [
    "electronics", "Electronics", "ELECTRONICS", "  electronics  ", "eLeCtRoNiCs",
])
def test_merchant_category_casing_does_not_move_the_score(real_scorer, variant):
    # to_features upper-cases and strips, so these must be the same transaction
    # as far as the pipeline is concerned. If this drifts, the OneHotEncoder is
    # silently mapping variants to its unknown category.
    baseline = real_scorer.score(make_transaction(merchant_category="ELECTRONICS"))
    variant_score = real_scorer.score(make_transaction(merchant_category=variant))

    assert variant_score.probability == pytest.approx(baseline.probability, abs=1e-12)


def test_spaces_and_underscores_are_the_same_category(real_scorer):
    spaced = real_scorer.score(make_transaction(merchant_category="home goods"))
    joined = real_scorer.score(make_transaction(merchant_category="HOME_GOODS"))

    assert spaced.probability == pytest.approx(joined.probability, abs=1e-12)


def test_unknown_category_is_absorbed_not_raised(real_scorer):
    # handle_unknown="ignore" is what keeps a new MCC from taking the service
    # down at 3am. Assert it, because it is one constructor argument away.
    score = real_scorer.score(make_transaction(merchant_category="CRYPTO KIOSK"))

    assert 0.0 <= score.probability <= 1.0


def test_larger_amounts_score_higher(real_scorer):
    amounts = [10.0, 100.0, 1_000.0, 10_000.0, 100_000.0]
    probabilities = [real_scorer.score(make_transaction(amount_sar=a)).probability
                     for a in amounts]

    assert probabilities == sorted(probabilities), (
        f"expected monotonically rising risk with amount, got {probabilities}")
    assert probabilities[-1] > probabilities[0]


def test_night_transactions_score_higher_than_daytime(real_scorer):
    night = real_scorer.score(make_transaction(
        timestamp=datetime(2026, 7, 5, 3, 0, tzinfo=UTC)))
    day = real_scorer.score(make_transaction(
        timestamp=datetime(2026, 7, 5, 14, 0, tzinfo=UTC)))

    assert night.probability > day.probability


def test_probability_stays_in_range_across_the_input_space(real_scorer):
    for amount in (0.01, 1.0, 999_999.0):
        for channel in ("pos", "ecom", "atm", "transfer"):
            for hour in (0, 5, 6, 23):
                score = real_scorer.score(make_transaction(
                    amount_sar=amount, channel=channel,
                    timestamp=datetime(2026, 7, 5, hour, tzinfo=UTC)))
                assert 0.0 <= score.probability <= 1.0


def test_scoring_is_deterministic(real_scorer):
    scores = {real_scorer.score(make_transaction()).probability for _ in range(5)}
    assert len(scores) == 1


def test_model_version_comes_from_the_artefact(real_scorer):
    assert real_scorer.score(make_transaction()).model_version == "v3.2.0"
