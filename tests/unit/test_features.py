"""Feature extraction. This is the code path that the notebook got wrong by
recomputing amount_log a second way, so the normalisation rules are pinned
here rather than left to the model to absorb."""
import math
from datetime import UTC, datetime

import pytest

from tests.support import make_transaction


@pytest.mark.unit
@pytest.mark.parametrize("raw,expected", [
    ("electronics", "ELECTRONICS"),
    ("Electronics", "ELECTRONICS"),
    ("ELECTRONICS", "ELECTRONICS"),
    ("home goods", "HOME_GOODS"),
    ("  grocery  ", "GROCERY"),
    ("Fast Food Outlet", "FAST_FOOD_OUTLET"),
])
def test_merchant_category_is_normalised(raw: str, expected: str) -> None:
    features = make_transaction(merchant_category=raw).to_features()
    assert features.values["mcc"] == expected


@pytest.mark.unit
@pytest.mark.parametrize("hour,expected", [
    (0, 1), (3, 1), (5, 1),   # night runs up to but not including 06:00
    (6, 0), (7, 0), (12, 0), (22, 0), (23, 0),
])
def test_is_night_boundary(hour: int, expected: int) -> None:
    timestamp = datetime(2026, 7, 5, hour, 0, tzinfo=UTC)
    features = make_transaction(timestamp=timestamp).to_features()
    assert features.values["is_night"] == expected
    assert features.values["hour_of_day"] == hour


@pytest.mark.unit
@pytest.mark.parametrize("amount", [0.01, 1.0, 412.5, 10_000.0, 999_999.0])
def test_amount_log_is_log1p(amount: float) -> None:
    features = make_transaction(amount_sar=amount).to_features()
    assert features.values["amount_log"] == pytest.approx(math.log1p(amount))


@pytest.mark.unit
def test_amount_log_is_monotonic_in_amount() -> None:
    amounts = [1.0, 10.0, 100.0, 1_000.0, 10_000.0]
    logs = [make_transaction(amount_sar=a).to_features().values["amount_log"] for a in amounts]
    assert logs == sorted(logs)


@pytest.mark.unit
def test_feature_set_is_exactly_what_the_pipeline_expects() -> None:
    features = make_transaction().to_features()
    assert set(features.values) == {"amount_log", "channel", "mcc", "hour_of_day", "is_night"}


@pytest.mark.unit
def test_channel_is_serialised_as_its_value_not_the_enum() -> None:
    features = make_transaction(channel="pos").to_features()
    assert features.values["channel"] == "pos"
    assert isinstance(features.values["channel"], str)
