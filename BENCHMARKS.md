# Benchmarks

Host: Apple Silicon (arm64), macOS 25.5, Docker Engine 29.5.2, Compose 5.5.0.
All images built and run natively for `linux/arm64` — no `--platform linux/amd64`
emulation, so the container numbers are not paying a QEMU tax.

Load driver: 1000 POSTs to `/v1/predict` with `payloads/sample.json` over
keep-alive connections, at concurrency 1 and 20. Every run returned 1000× 200.

## Lab 3 — image size and build time

| Image | Dockerfile | Base | Size | Cold build | Warm rebuild (1-line `routes.py` edit) |
|---|---|---|---|---|---|
| `fraud-service:naive` | `Dockerfile.naive` | `python:3.13` | **2.32 GB** | 133 s (`--no-cache`) | n/a — `COPY . .` precedes the install, so every edit reinstalls everything |
| `fraud-service:slim` | `Dockerfile` | `python:3.13-slim` (multi-stage) | **744 MB** | 249 s | **16 s** |

3.1× smaller. The gap comes from three things, in order of size:

1. `python:3.13` carries a full build toolchain and headers (~1.0 GB before a
   single dependency lands); `python:3.13-slim` is ~150 MB.
2. `build-essential` is installed in the builder stage only and never reaches
   the runtime stage.
3. The naive image ships the whole build context (`data/`, the notebook, the
   editable-install source tree); the runtime stage ships only `/opt/venv`,
   the installed wheel, and `models/`.

The remaining 744 MB is dominated by scipy/numpy/scikit-learn/pandas — that is
the real floor for this dependency set, not packaging slack.

### Cache discipline

Warm rebuild after editing one line of `src/fraud_service/api/routes.py`:
**16 s**, with `RUN pip install -r requirements.txt` and
`COPY --from=builder /opt/venv /opt/venv` both reported as `Using cache`.

Two ordering decisions make that work:

- `requirements.txt` is copied and installed *before* `COPY src ./src`, so a
  source edit never invalidates the dependency layer.
- The application is **not** installed into `/opt/venv` in the builder. The
  builder emits a wheel; the runtime stage copies the venv (a large,
  source-independent layer) and then installs the wheel in a separate, tiny
  layer. Installing the app into the venv instead made the venv layer
  source-dependent and pushed the warm rebuild to 35 s, because the ~700 MB
  `COPY --from=builder` had to run again on every edit.

## Lab 3 — time to ready

`docker compose up` (images already built) → both services `healthy`:

| Milestone | Seconds from `up` |
|---|---|
| `docker compose up -d` returns | 5.5 |
| `redis` healthy | 5.6 |
| `api` healthy | **10.7** |

The API process itself is ready far sooner — `model_loaded version=v3.2.0
seconds=0.639`, warm-up prediction included. The remaining ~10 s is scheduling,
not work: the API is gated behind `depends_on: redis: condition: service_healthy`
(~5.6 s), and its own healthcheck is only sampled every `interval: 5s`.
Tightening `interval`/`start_period` moves this number; it will not make the
service ready any sooner.

## Latency: container vs bare metal

Bare metal = `uvicorn` in the local `.venv` (CPython 3.11) on `127.0.0.1:8090`.
Container = the compose stack, published on `127.0.0.1:8080` (host port 8000 was
already occupied by an unrelated `ssh` tunnel on this machine).

### Concurrency 1

| Target | RPS | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| Bare metal | 319.8 | 3.08 ms | 3.36 ms | 3.64 ms | 8.09 ms |
| Container | 268.1 | 3.64 ms | 4.12 ms | 5.35 ms | 27.38 ms |

### Concurrency 20

| Target | RPS | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| Bare metal | 344.4 | 56.18 ms | 72.88 ms | 96.92 ms | 105.82 ms |
| Container | 309.3 | 63.34 ms | 85.49 ms | 99.11 ms | 120.66 ms |

Single-request latency from the host:
`curl -w "%{time_total}"` → 0.0076 s bare metal, 0.0093 s containerised
(`X-Response-Time-Ms` header on the same request: 9.3 ms).

The container costs ~0.6 ms at p50 and ~10 % RPS. That is the Docker Desktop
VM's network path (`gVisor`/`vmnet` port forwarding), not the runtime: the
in-container healthcheck sees the same app. The p99 gap closes almost entirely
under concurrency — at 20 in-flight requests both targets are bounded by the
same thing, sklearn inference on the threadpool, not by the network hop.

## Correctness of the containerised service

```
GET  /v1/health                       200  {"status":"ok"}
GET  /v1/ready                        200  {"status":"ready"}
POST /v1/predict  (sample.json)       200  {"transaction_id":"TXN-2026-00042",
                                            "fraud_probability":0.557066,
                                            "decision":"allow",
                                            "model_version":"v3.2.0",
                                            "trace_id":"989f8779c78b494a"}
POST /v1/predict  (amount_sar: -5)    422
POST /v1/predict  (unknown field)     422
docker exec sda-api-1 whoami          app   (uid=10001 gid=10001)
```

`fraud_probability` is byte-identical to the Lab 2 bare-metal result — the
container changes packaging, not scoring.
