"""The corpus is the contract: every malformed file 4xx, every valid file 200.

Parametrised over the directories, so a payload added to the repo is covered
the moment it lands."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

MALFORMED = sorted(Path("payloads/malformed").glob("*.json"))
VALID = sorted(Path("payloads/valid").glob("*.json"))
JSON_HEADERS = {"content-type": "application/json"}


def test_the_corpus_is_actually_present():
    # A glob matching nothing would make every test below vacuously pass.
    assert len(MALFORMED) >= 50
    assert len(VALID) >= 20


@pytest.mark.parametrize("path", MALFORMED, ids=lambda p: p.stem)
def test_malformed_payload_is_rejected(client, path: Path):
    # Raw bytes, not json=: part of the corpus is not valid JSON at all.
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
    # The other half of the guard: tightening must not reject good payloads.
    response = client.post("/v1/predict", content=path.read_bytes(), headers=JSON_HEADERS)

    assert response.status_code == 200, f"{path.name} returned {response.status_code}"
    assert response.json()["transaction_id"]


def test_no_rejection_leaks_the_input_back_verbatim(client):
    # The envelope names fields, never values - no reflection point.
    payload = Path("payloads/malformed/script_injection_merchant.json").read_bytes()
    response = client.post("/v1/predict", content=payload, headers=JSON_HEADERS)

    assert "<script>" not in response.text
