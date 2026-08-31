"""Wire contract - what a CLIENT sends/receives. Kept separate from
domain.entities.Transaction on purpose: this shape can change (API v2)
without touching what "a transaction" means internally, and vice versa."""
import re

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from fraud_service.domain.entities import Channel, Decision, Transaction

# Identifiers are ASCII tokens with no surrounding whitespace. Anchored at both
# ends so "        ", " CUST-0042 " and "TXN-<emoji>" are rejected at the edge
# rather than reaching the feature code as a category of their own.
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]*[A-Za-z0-9]$"
# Categories additionally allow spaces and & (to_features folds them to _),
# which excludes "   ", control characters and markup.
CATEGORY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 &._-]*[A-Za-z0-9]$"
NUMERIC = re.compile(r"^[+-]?\d+(\.\d+)?$")


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields = typo = reject loudly

    transaction_id: str = Field(min_length=8, max_length=64, pattern=ID_PATTERN)
    amount_sar: float = Field(gt=0, le=1_000_000)
    channel: Channel
    merchant_category: str = Field(min_length=2, max_length=40, pattern=CATEGORY_PATTERN)
    customer_id: str = Field(min_length=4, max_length=64, pattern=ID_PATTERN)
    timestamp: AwareDatetime

    @field_validator("amount_sar", mode="before")
    @classmethod
    def reject_bool(cls, value: object) -> object:
        # bool is a subclass of int, so pydantic would read `true` as 1.0.
        if isinstance(value, bool):
            raise ValueError("amount_sar must be a number, not a boolean")
        return value

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_iso_8601(cls, value: object) -> object:
        # Epoch seconds/millis are ambiguous at this boundary - 1751753640000 is
        # a valid instant in two different units. Demand an explicit ISO-8601
        # string and let the client resolve it.
        if not isinstance(value, str):
            raise ValueError("timestamp must be an ISO-8601 string")
        if NUMERIC.match(value.strip()):
            raise ValueError("timestamp must be an ISO-8601 string, not an epoch value")
        return value

    def to_domain(self) -> Transaction:
        return Transaction(**self.model_dump())


class PredictResponse(BaseModel):
    transaction_id: str
    fraud_probability: float = Field(ge=0, le=1)
    decision: Decision
    model_version: str
    trace_id: str


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """One envelope for every failure, so clients parse one shape."""

    error: ErrorDetail
    trace_id: str
