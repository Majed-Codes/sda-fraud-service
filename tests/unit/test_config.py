"""Settings validate at startup or not at all."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from fraud_service.config import Settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in [k for k in __import__("os").environ if k.startswith("FRAUD_")]:
        monkeypatch.delenv(key, raising=False)


def test_defaults_are_usable():
    settings = Settings()
    assert settings.block_threshold == 0.85
    assert settings.log_level == "INFO"
    assert settings.model_path.is_file()


def test_missing_artefact_fails_at_construction(monkeypatch, tmp_path):
    monkeypatch.setenv("FRAUD_MODEL_PATH", str(tmp_path / "absent.joblib"))
    with pytest.raises(ValidationError) as excinfo:
        Settings()
    assert "model_path" in str(excinfo.value)
    assert "artefact not found" in str(excinfo.value)


def test_a_directory_is_not_an_artefact(monkeypatch, tmp_path):
    monkeypatch.setenv("FRAUD_MODEL_PATH", str(tmp_path))
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("value", ["8.5", "0.4", "-1"])
def test_threshold_is_bounded(monkeypatch, value):
    monkeypatch.setenv("FRAUD_BLOCK_THRESHOLD", value)
    with pytest.raises(ValidationError) as excinfo:
        Settings()
    assert "block_threshold" in str(excinfo.value)


def test_unknown_log_level_is_rejected(monkeypatch):
    monkeypatch.setenv("FRAUD_LOG_LEVEL", "CHATTY")
    with pytest.raises(ValidationError) as excinfo:
        Settings()
    assert "log_level" in str(excinfo.value)


def test_a_typo_is_a_crash_not_a_default(monkeypatch):
    monkeypatch.setenv("FRAUD_BLOCK_THRESHOLDD", "0.9")
    with pytest.raises(ValidationError) as excinfo:
        Settings()
    assert "FRAUD_BLOCK_THRESHOLDD" in str(excinfo.value)


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("FRAUD_BLOCK_THRESHOLD", "0.60")
    monkeypatch.setenv("FRAUD_GIT_SHA", "abc1234")
    settings = Settings()
    assert settings.block_threshold == 0.60
    assert settings.git_sha == "abc1234"


def test_token_never_renders_in_the_clear(monkeypatch):
    monkeypatch.setenv("FRAUD_REGISTRY_TOKEN", "ghp_shouldNeverAppear")
    settings = Settings()
    assert "shouldNeverAppear" not in repr(settings)
    assert "shouldNeverAppear" not in str(settings.registry_token)
    assert settings.registry_token is not None
    assert settings.registry_token.get_secret_value() == "ghp_shouldNeverAppear"


def test_model_path_accepts_an_explicit_path():
    settings = Settings(model_path=Path("models/fraud_xgb_v3.joblib"))
    assert settings.model_path.name == "fraud_xgb_v3.joblib"
