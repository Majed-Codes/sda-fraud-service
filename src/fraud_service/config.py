"""Typed configuration, validated once at startup.

Everything reads from FRAUD_*. A misspelled variable is a startup crash, not a
default quietly taking effect.
"""
import os
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FRAUD_",
        env_file=".env",
        extra="forbid",
    )

    model_path: Path = Field(
        Path("models/fraud_xgb_v3.joblib"), description="joblib bundle to serve")
    block_threshold: float = Field(
        0.85, ge=0.5, le=0.99, description="risk-approved block threshold")
    log_level: LogLevel = Field("INFO")
    log_json: bool = Field(True, description="false gives readable console logs in dev")
    git_sha: str = Field("dev", description="injected by CI")
    redis_url: str = Field("redis://redis:6379/0")
    registry_token: SecretStr | None = Field(None)

    @field_validator("model_path")
    @classmethod
    def artefact_must_exist(cls, value: Path) -> Path:
        if not value.is_file():
            raise ValueError(
                f"artefact not found at {value.absolute()} - set FRAUD_MODEL_PATH")
        return value

    @field_validator("registry_token", mode="before")
    @classmethod
    def empty_means_unset(cls, value: object) -> object:
        # An unfilled line in an env file would otherwise read as SecretStr("").
        return None if value == "" else value

    @model_validator(mode="after")
    def reject_unknown_variables(self) -> "Settings":
        # extra="forbid" covers the .env file and init kwargs but not the
        # environment, so FRAUD_BLOCK_THRESHOLDD would otherwise be ignored.
        # Matched case-insensitively because pydantic-settings reads it that way.
        known = {f"fraud_{name}" for name in type(self).model_fields}
        unknown = sorted(k for k in os.environ
                         if k.lower().startswith("fraud_") and k.lower() not in known)
        if unknown:
            raise ValueError(f"unknown FRAUD_* variables: {', '.join(unknown)}")
        return self
