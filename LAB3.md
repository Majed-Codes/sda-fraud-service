# Lab 3 — Containerise the Fraud Service

**Duration:** 50 minutes · **Pairs**
Setup: continue on `main` from your Lab 2 commit — see `LAB3-SETUP.md`.
Docker Desktop (or Colima) must be running: confirm with
`docker run hello-world` first.

## Objective

Produce a slim, non-root, healthchecked Docker image for the service, plus
a `docker-compose.yml` dev stack. Measure the difference discipline makes.

## Tasks

1. **(5 min)** Write `.dockerignore` first (what should Docker never see in
   its build context?). Then write a **naive** Dockerfile — a single stage,
   `COPY . .` before installing dependencies, no non-root user. Build it and
   record the image size and build time.
2. **(15 min)** Author the real Dockerfile, following this morning's
   lecture: multi-stage (a builder stage with the full toolchain, a slim
   runtime stage with only what's needed to run), a non-root user, and a
   `HEALTHCHECK` against `/v1/ready` — not `/v1/health`. Build it and record
   the size again.
3. **(5 min)** Prove cache discipline: edit one line in `routes.py`, rebuild,
   and confirm the rebuild is fast and the dependency-install layer shows
   as cached. If it isn't, look at the order of your `COPY` instructions.
4. **(10 min)** Write `docker-compose.yml`: the service plus a Redis
   container, with the API's healthcheck gating on Redis's. Bring it up and
   confirm `docker compose ps` shows both containers `healthy`.
5. **(10 min)** Run an end-to-end smoke test against the running container
   (curl `/v1/ready`, then `/v1/predict` with `payloads/sample.json`).
   Record the container's latency next to Lab 2's bare-metal numbers in
   `BENCHMARKS.md`.
6. **(5 min)** Measure time-to-ready (how long from `docker compose up`
   until the healthcheck goes green). Commit.

## Definition of done

- Two recorded image sizes in `BENCHMARKS.md`: naive vs multi-stage. The
  gap should be large — if it isn't, something about the naive build wasn't
  actually naive.
- The real image is non-root (`docker exec <container> whoami` should not
  say `root`).
- `docker compose ps` shows every service `healthy`, not just `running`.
- A warm rebuild after a one-line source edit takes well under a minute.

## If you're on Apple Silicon

You may need `--platform linux/amd64` depending on what you're targeting.
Ask your instructor if a build fails with an architecture-related error.

## Stuck?

Talk to your pair, then flag your instructor rather than skipping ahead.
