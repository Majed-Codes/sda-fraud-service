# Lab 2 — Build and Harden the Prediction API

**Duration:** 2 × 50 min (Part A today, Part B tomorrow morning) · **Pairs**
Setup: continue on `main` from your Lab 1 commit — see `LAB2-SETUP.md`.

## Objective

Expose the Lab 1 scorer as a FastAPI service: `/v1/predict`, `/v1/health`,
`/v1/ready`, with strict request validation and a consistent error envelope.
Then harden it and prove it holds up under load.

## Part A — today

1. **(10 min) `api/schemas.py`** — `PredictRequest`/`PredictResponse` +
   an error envelope, matching the contract table from lecture. Reject
   unknown fields loudly (`extra="forbid"`) and bound every numeric/string
   field (no negative amounts, no unbounded lengths).
2. **(15 min) `api/app.py`** — the FastAPI app factory: load the model in
   `lifespan`, wire the scorer, add a middleware that stamps a trace id and
   timing header on every response.
3. **(15 min) `api/routes.py`** — `/v1/predict`, `/v1/health`, `/v1/ready`
   with the status codes covered in lecture (what should "model still
   loading" return? what about a validation failure?).
4. **(10 min)** Run `fastapi dev src/fraud_service/api/app.py` and exercise
   it via `/docs`: one valid request, one with a negative amount, one with
   an unrecognised field. Confirm each behaves the way the lecture's
   contract table says it should.

## Part B — tomorrow, Day 2 Hour 1

5. **(15 min)** Add a warm-up prediction call during startup. Measure
   first-request latency before and after with
   `curl -w "%{time_total}"`.
6. **(10 min)** Add a global exception handler so an unhandled error never
   leaks a stack trace to the client — only an error envelope with a trace
   id. Prove it: add a temporary route that deliberately raises, hit it,
   check the response, then remove the route.
7. **(15 min)** Load-test with `hey` against `/v1/predict` (a sample
   payload is at `payloads/sample.json`). Record p50/p99/RPS in a new
   `BENCHMARKS.md`.
8. **(10 min)** Commit: `feat(api): prediction endpoint with validation, health, tracing`

## Definition of done

- `curl -s localhost:8000/v1/predict -d @payloads/sample.json -H "content-type: application/json"`
  returns something shaped like:
  ```json
  {"transaction_id":"TXN-2026-00042","fraud_probability":0.557066,
   "decision":"allow","model_version":"v3.2.0","trace_id":"a1b2c3d4e5f60718"}
  ```
- `/v1/health` and `/v1/ready` return correct status codes before and after
  the model finishes loading.
- The malformed requests you tried in task 4 all come back as 4xx, never
  200 and never a raw 500 with a stack trace.
- `BENCHMARKS.md` has real numbers from your own `hey` run, not guesses.

## If your load-test numbers look wrong

If throughput collapses or latency spikes under concurrency, that's
diagnosable from what was covered in lecture about how FastAPI schedules
route handlers — think about what kind of work your `/v1/predict` route is
doing before you assume it's a load-testing fluke.

## Stuck?

Talk to your pair, then flag your instructor rather than skipping ahead.
