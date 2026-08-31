# Lab 6 — Harden Config, Secrets & Logs

**Duration:** 35 minutes · **Pairs**
Setup: continue on `main` from your Lab 5 commit — see `LAB6-SETUP.md`.

## Objective

Replace ad-hoc configuration with a typed, validated settings object; make
startup fail fast and clearly on bad config; convert logging to correlated
structured JSON; and run a real secret-leak drill.

## Tasks

1. **(10 min)** Implement a typed `Settings` object (pydantic-settings) with
   validation on the fields that matter (does the model path actually
   exist? is the log level one of the allowed values?). Wire it into the
   app's startup. Then find and remove every scattered `os.environ` read
   left in `src/` outside your new settings module —
   `grep -rn "os.environ" src/` will find them. There are three.
2. **(5 min)** Prove fail-fast: point `FRAUD_MODEL_PATH` at a file that
   doesn't exist and start the app. Compare what you see to what a
   *missing validation* version would do instead (a 500 on the first real
   request, not a clear error at startup).
3. **(10 min)** Wire structured JSON logging: every log line should carry a
   trace id, and a `prediction_served` event should fire per request with
   the decision and a *bucketed* probability — never the raw customer id or
   amount together with the score. Run a small burst of requests and pipe
   the logs through `jq` to compute a latency percentile from the logs
   alone, with no separate load-test tool involved.
4. **(5 min)** Secret drill: run `gitleaks detect` against the repo. It
   should find something in `configs/dev.env`. Write a two-step response in
   `INCIDENT.md` — think about *order*: is deleting the file from history
   enough on its own, or does something have to happen first?
5. **(5 min)** Confirm your masking actually works: deliberately log a
   secret value and check what shows up in the output. Remove the line
   once you've confirmed it. Commit.

## Definition of done

- Starting the app with a bad `FRAUD_MODEL_PATH` fails immediately with a
  message naming the field — not a crash three requests later.
- `grep -rn "os.environ" src/` returns nothing outside your settings module.
- Every log line is valid JSON (`jq` will fail loudly on the first one that
  isn't).
- `gitleaks detect` on your repo comes back clean once you've actually
  fixed the leak — not just documented it.
- `INCIDENT.md` states the right order of operations, not just "delete it."

## Stuck?

Talk to your pair, then flag your instructor rather than skipping ahead.
