# Lab 4 — Build the Test Suite

**Duration:** 50 minutes · **Pairs**
Setup: continue on `main` from your Lab 3 commit — see `LAB4-SETUP.md`.

## Objective

Build a three-level pytest suite — unit, integration, behavioural — with
meaningful coverage, not coverage theatre. `payloads/valid/` and
`payloads/malformed/` already exist in the repo for the integration corpus.

## Tasks

1. **(10 min) `tests/conftest.py`** — a test double for the model (returns a
   fixed probability, no sklearn involved) and a fixture that builds a
   `TestClient` with the scorer dependency overridden to use it. This is
   the payoff of the dependency-injection design from Module 1 — if you're
   fighting to make this work, the seam probably isn't where lecture said
   it should be.
2. **(10 min) Unit tests** — parametrised tests for the decision-band policy
   (allow / review / block boundaries) and for feature extraction (does
   casing get normalised? is the night flag correct at the boundary hour?).
   Run `pytest -m unit` — should finish in well under a second.
3. **(10 min) Integration tests** — one test asserting the full contract on
   a valid request (status code, envelope shape, headers). One
   parametrised test running every file in `payloads/malformed/` through
   `/v1/predict` and asserting each comes back 4xx. One test proving a
   forced exception never leaks a stack trace to the client.
4. **(10 min) Behavioural tests** — against the *real* model artefact (a
   session-scoped fixture, loaded once): an invariance test (does casing
   change the merchant category score?), a directional test (does a much
   larger amount raise or lower the score?), and a golden-file test against
   `data/golden_scores_v3.csv`.
5. **(5 min)** Run the full suite with coverage. Read the `term-missing`
   report — don't just look at the percentage — and add **one** test that
   closes the most meaningful gap you can find, not the easiest one.
6. **(5 min)** Commit, and record the suite's timing.

## Definition of done

- `pytest -m unit` passes in well under a second.
- `pytest -m "not slow"` passes with branch coverage ≥ 80% on
  `domain`/`service`/`api`.
- Every file in `payloads/malformed/` is asserted against, not just
  eyeballed.
- The golden-file test actually loads the real model artefact — if it's
  using your fixed test double, it isn't testing anything about skew.

## Stuck?

Talk to your pair, then flag your instructor rather than skipping ahead.
