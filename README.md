# fraud-service

Fraud scoring for card transactions, served over HTTP. `SDA-AIE-113`.

A transaction goes in, a probability and a decision come out:

```json
{"transaction_id":"TXN-2026-00042","fraud_probability":0.557066,
 "decision":"allow","model_version":"v3.2.0","trace_id":"a1b2c3d4e5f60718"}
```

## Run it

Requires Python 3.11+ and Docker.

```bash
python -m venv .venv && source .venv/bin/activate
make install
make up          # compose stack on :8080, waits for healthy
make smoke       # builds the image and asserts against it
```

Without Docker:

```bash
make serve       # fastapi dev on :8000
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| `POST` | `/v1/predict` | Scores one transaction. 422 on anything malformed. |
| `GET` | `/v1/health` | Liveness. No I/O, always 200 while the process is up. |
| `GET` | `/v1/ready` | Readiness. 503 until the model is loaded and wired. |

Every response carries `X-Trace-Id` and `X-Response-Time-Ms`. Failures return one
envelope shape — `{"error": {"code", "message"}, "trace_id"}` — and never a traceback.

```bash
curl -s localhost:8080/v1/predict -H 'content-type: application/json' \
     -d @payloads/sample.json
```

## Test

```bash
make test-unit   # 36 tests, under a second
make test        # everything except the slow golden sweep
make test-all    # including the 5000-row golden file
make cov         # branch coverage over domain/service/api
make lint        # ruff, mypy --strict, import-linter
```

`payloads/valid/` and `payloads/malformed/` are the wire contract: every file in
the first must score, every file in the second must be rejected. Both directions
are asserted.

## Layout

```
src/fraud_service/
  domain/      entities, feature extraction, decision policy - stdlib + pydantic only
  service/     scoring orchestration against a Model protocol
  adapters/    the only place that imports sklearn or joblib
  api/         schemas, routes, error envelope, app factory
  batch.py     CSV entrypoint - scores data/transactions_sample.csv
```

Dependencies point inward only, and `import-linter` fails the build if that stops
being true.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Feature cache, set by compose |

The model is baked into the image at `models/fraud_xgb_v3.joblib`; the block
threshold is `0.85`, wired in `api/app.py`.

## Everything else

- `BENCHMARKS.md` — image sizes, build and rebuild times, cold start, latency,
  suite timings. Measured on this machine, reproducible with `scripts/loadtest.py`.
- `DECISIONS.md` — the six calls worth arguing about, and why they went that way.
- `INCIDENT.md` — the secret-leak drill and the response order.
- `.github/workflows/ci.yml` — lint, test and secret scan in parallel, image
  smoke, GHCR publish on `main` tagged by commit SHA.
- `make help` lists every target.
