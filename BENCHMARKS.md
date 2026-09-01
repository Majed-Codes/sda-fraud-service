# Benchmarks

Host: Apple Silicon (arm64), macOS 25.5, Docker Engine 29.5.2, Compose 5.5.0.
Images build and run natively for `linux/arm64` — no `--platform linux/amd64`
emulation, so the container numbers pay no QEMU tax.

Load driver: `scripts/loadtest.py` — 1000 POSTs to `/v1/predict` with
`payloads/sample.json` over keep-alive connections, at concurrency 1 and 20.
Every run below returned 1000× 200.

```bash
python scripts/loadtest.py 127.0.0.1 8080 1000 20
```

## Image size and build time

| Image | Dockerfile | Base | Image size | Pull size | Cold build | Warm rebuild |
|---|---|---|---|---|---|---|
| `fraud-service:naive` | `Dockerfile.naive` | `python:3.13` | **1715 MB** | 572 MB | 133 s (`--no-cache`) | n/a - `COPY . .` precedes the install |
| `fraud-service:slim` | `Dockerfile` | `python:3.13-slim`, multi-stage | **437 MB** | 118 MB | 195 s | **15 s** |

**3.9x smaller, and under the 500 MB capstone gate.**

### Which size number is the size number

Docker Desktop's containerd image store reports three different figures for the
same image, and they are not interchangeable:

| Metric | slim | How to read it |
|---|---|---|
| Sum of layer sizes (`docker history`) | **437 MB** | The uncompressed image size - what `docker images` reports on a classic Docker install, and what "image size" conventionally means |
| `docker image inspect --format '{{.Size}}'` | 118 MB | Compressed content size: what a `docker pull` actually transfers |
| Docker Desktop's `docker images` DISK USAGE column | 561 MB | Extracted snapshot on this host, including snapshotter overhead. Host bookkeeping, not a property of the image |

Where the 1278 MB difference from the naive build goes, largest first:

1. `python:3.13` carries a full build toolchain and headers - ~1.0 GB before a
   single dependency lands. `python:3.13-slim` is ~215 MB.
2. `build-essential` exists only in the builder stage.
3. The naive image ships the whole build context - `data/`, the notebook, the
   editable-install source tree.
4. Builder-side pruning: site-package `tests/` directories, `.pyi` stubs, and
   `strip --strip-unneeded` over every `.so` (the numeric stack ships large
   debug symbol tables).
5. `pip`, `setuptools` and `pkg_resources` are removed **in the builder**,
   before the venv is copied. Deleting them in the runtime stage - which this
   Dockerfile used to do - only writes whiteout entries; the bytes stay in the
   layer that already shipped them. The runtime stage unpacks the application
   wheel with `python -m zipfile`, so pip never enters the final image.
6. `websockets` and `watchfiles` are dropped from `requirements.txt`. They
   arrive via `uvicorn[standard]`, and this service has no WebSocket route and
   never runs `--reload` in a container. `uvloop` and `httptools` stay - those
   are the ones that carry the throughput in the tables below.

### What not to prune

Deleting `__pycache__` saves 48 MB and takes cold start from **1.0 s to 32.3 s**:
with `PYTHONDONTWRITEBYTECODE=1` the interpreter recompiles numpy, scipy, pandas
and scikit-learn on *every* container start and can never cache the result. It
was measured, reverted, and is recorded here because the saving looks free in a
size table and is anything but.

### Cache discipline

Warm rebuild after editing one line of `src/fraud_service/api/routes.py`:
**15 s**, with both `RUN pip install -r requirements.txt` and
`COPY --from=builder /opt/venv /opt/venv` reported `CACHED`.

Two ordering decisions buy that:

- `requirements.txt` is copied and installed *before* `COPY src ./src`, so a
  source edit cannot invalidate the dependency layer. Pinning it separately
  from `pyproject.toml` is what makes that layer stable.
- The application is **not** installed into `/opt/venv` in the builder. The
  builder emits a wheel; the runtime stage copies the venv — a large,
  source-independent layer — and installs the wheel in its own small layer.
  Installing the app into the venv instead makes that ~700 MB
  `COPY --from=builder` source-dependent and pushes the warm rebuild to 35 s,
  measured. The dependency-install layer stays cached either way, which is
  why layer count alone is a bad proxy for cache health.

## Time to ready

`docker compose up` with images already built:

| Milestone | Seconds from `up` |
|---|---|
| `docker compose up -d` returns | 6.2 |
| `redis` healthy | 6.4 |
| `api` healthy | **11.6** |

The API process is ready long before that: `model_loaded version=v3.2.0
seconds=0.714`, warm-up prediction included. The remaining ~11 s is scheduling,
not work — the API is gated behind `depends_on: redis: condition:
service_healthy` (~6.4 s) and its own healthcheck is sampled only every
`interval: 5s`. Tightening `interval`/`start_period` moves this number; it will
not make the service ready any sooner.

### Container cold start

The compose figure above is gated by healthcheck polling. The container's own
cold start, measured as `docker run` to a 200 on `/v1/ready`:

| Stage | Seconds |
|---|---|
| `docker run -d` returns | 0.18 |
| interpreter start + import fastapi/pandas/sklearn | ~0.2 |
| `SklearnModel.load` + warm-up prediction | 0.66 |
| **`/v1/ready` returns 200** | **1.01** |

First `/v1/predict` after that: 6.8 ms, against a warm p50 of 4.18 ms. The
Lab 2 startup warm-up is doing its job — without it the first request pays
sklearn's lazy init instead.

So the 11.6 s to `healthy` is ~85 % waiting, not working: 6.4 s of it is the
Redis dependency gate and the rest is healthcheck `interval: 5s` granularity.
An orchestrator with a 1 s probe interval would see this container ready in
about 2 s.

## Latency: container vs bare metal

Bare metal = `uvicorn` in the local `.venv` (CPython 3.11) on `127.0.0.1:8090`.
Container = the compose stack on `127.0.0.1:8080` (host port 8000 is occupied by
an unrelated `ssh` tunnel on this machine).

### Concurrency 1

| Target | RPS | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| Bare metal | 313.8 | 3.12 ms | 3.54 ms | 3.89 ms | 10.08 ms |
| Container | 249.0 | 3.68 ms | 5.04 ms | 10.99 ms | 61.80 ms |

### Concurrency 20

| Target | RPS | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| Bare metal | 333.9 | 57.36 ms | 76.54 ms | 99.07 ms | 119.42 ms |
| Container | 302.2 | 64.59 ms | 89.69 ms | 107.74 ms | 137.64 ms |

Single request from the host, `curl -w "%{time_total}"`: 0.0056 s bare metal,
0.0250 s containerised on a cold connection (`X-Response-Time-Ms` for the same
request shows the app spent ~9 ms of it).

The container costs ~0.6 ms at p50 and ~10 % RPS. That is the Docker Desktop
VM's port-forwarding path, not the runtime — the in-VM healthcheck sees the same
app. Under concurrency the gap narrows in relative terms: at 20 in-flight
requests both targets are bounded by the same thing, sklearn inference on
FastAPI's threadpool, not by the network hop. Note both plateau near ~330 RPS
regardless of concurrency — that is the single-worker CPU ceiling, and it is
what `--workers` would move, not the container boundary.

## Containerised service, verified

```
GET  /v1/health                      200  {"status":"ok"}
GET  /v1/ready                       200  {"status":"ready"}
POST /v1/predict  (sample.json)      200  {"transaction_id":"TXN-2026-00042",
                                           "fraud_probability":0.557066,
                                           "decision":"allow",
                                           "model_version":"v3.2.0",
                                           "trace_id":"fd7e809df4fc4448"}
POST /v1/predict  (amount_sar: -5)   422
POST /v1/predict  (unknown field)    422
docker exec sda-api-1 whoami         app   (uid=10001, gid=10001)
docker compose ps                    api healthy, redis healthy
```

`fraud_probability` is identical to the bare-metal Lab 2 result, before and
after the strip/prune pass. Containerising changed packaging, not scoring.

## Test suite (Lab 4)

194 tests. `pythonpath = ["src"]` in `pyproject.toml` means no editable install
is needed to run them.

| Selection | Tests | Wall time |
|---|---|---|
| `pytest -m unit` | 36 | **0.04 s** |
| `pytest -m "not slow"` | 192 | 4.3 s |
| `pytest` (everything) | 194 | 14.2 s |

The two `slow` tests are the full 5000-row golden sweep and its casing
round-trip. Everything else stays in the inner loop.

Branch coverage on `domain` / `service` / `api`, from `pytest -m "not slow"`:

| Module | Cover |
|---|---|
| `api/app.py` | 100% |
| `api/errors.py` | 100% |
| `api/routes.py` | 100% |
| `api/schemas.py` | 100% |
| `domain/entities.py` | 100% |
| `domain/policies.py` | 100% |
| `service/scorer.py` | 100% |
| **Total** | **100%** (189 statements, 16 branches) |

That total is a consequence, not a target. The report before the last test was
94%, and the missing lines were `lifespan` in `app.py` — the code that loads the
artefact, warms it and wires the scorer. It is the only uncovered region that
fails the container at *startup* rather than degrading a single response, which
is why `tests/behavioural/test_startup.py` closes that gap and not an easier one.

`batch.py` is deliberately outside the coverage target: it is a `main()`
composition root with no logic of its own.

## Startup warm-up: is it worth it? (Lab 2 task 5)

`lifespan` runs one throwaway prediction before the service reports ready.
Measured across 5 fresh model loads, timing the first `predict_proba` against
the median of 50 that follow it:

| | Median |
|---|---|
| First call after `SklearnModel.load` | 1.11 ms |
| Steady-state call | 1.07 ms |
| **Penalty avoided per load** | **0.04 ms** |

For *this* artefact the warm-up buys almost nothing. The first load in a fresh process cost 6.37 ms against 1.09-1.13 ms for the four
that followed, so the real one-time cost is process-wide - scipy/numpy import
and first-touch allocation - not per-model lazy init. A LogisticRegression
behind a OneHotEncoder has essentially no lazy state to build.

It stays in `lifespan` anyway: it costs ~5 ms once, it matters the moment the
artefact is swapped for something with real lazy initialisation (a boosted
ensemble, an ONNX session), and it proves the model can score before the service
reports ready.

Consistent with the container numbers above: first `/v1/predict` after a cold
start was 6.8 ms against a warm p50 of 4.18 ms.
