"""Every file in payloads/malformed must be rejected, and every file in
payloads/valid must be accepted. Parametrised over the directories rather
than a hand-written list, so a payload added to the repo is covered the
moment it lands."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

MALFORMED = sorted(Path("payloads/malformed").glob("*.json"))
VALID = sorted(Path("payloads/valid").glob("*.json"))
JSON_HEADERS = {"content-type": "application/json"}


def test_the_corpus_is_actually_present():
    # A glob that silently matched nothing would make every test below vacuous.
    assert len(MALFORMED) >= 50
    assert len(VALID) >= 20


@pytest.mark.parametrize("path", MALFORMED, ids=lambda p: p.stem)
def test_malformed_payload_is_rejected(client, path: Path):
    # Sent as raw bytes, not json=, because part of the corpus is not valid
    # JSON at all - serialising it through a dict would test the wrong thing.
    response = client.post("/v1/predict", content=path.read_bytes(), headers=JSON_HEADERS)

    assert 400 <= response.status_code < 500, (
        f"{path.name} returned {response.status_code}, not a client error")


@pytest.mark.parametrize("path", MALFORMED, ids=lambda p: p.stem)
def test_rejection_uses_the_error_envelope(client, path: Path):
    response = client.post("/v1/predict", content=path.read_bytes(), headers=JSON_HEADERS)

    body = response.json()
    assert set(body) == {"error", "trace_id"}
    assert set(body["error"]) == {"code", "message"}
    assert body["trace_id"] == response.headers["X-Trace-Id"]


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_payload_is_accepted(client, path: Path):
    # The other half of the guard: validation tight enough to reject the
    # malformed corpus must still admit every documented-good payload.
    response = client.post("/v1/predict", content=path.read_bytes(), headers=JSON_HEADERS)

    assert response.status_code == 200, f"{path.name} returned {response.status_code}"
    assert response.json()["transaction_id"]


def test_no_rejection_leaks_the_input_back_verbatim(client):
    # Reflecting a rejected merchant_category into the response body would
    # hand an attacker a reflection point; the envelope names fields, not values.
    payload = Path("payloads/malformed/script_injection_merchant.json").read_bytes()
    response = client.post("/v1/predict", content=payload, headers=JSON_HEADERS)

    assert "<script>" not in response.text
