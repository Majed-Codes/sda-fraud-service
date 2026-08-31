# Lab 1 — Refactor the Notebook into a Clean Package

**Duration:** 50 minutes · **Pairs** · Setup: see `LAB1-SETUP.md` —
this repo already starts at the right point.

## Objective

`notebook_v1.ipynb` scores fraud transactions using the provided model. It
works — but it has the notebook-to-production smells covered in this
morning's lecture. Turn it into a clean `src/fraud_service/` package
(`domain/`, `service/`, `adapters/`), wired together only in a new
`src/fraud_service/batch.py` entrypoint.

Data and model artefacts are already provided and won't change for the rest
of the course:

- `data/transactions_sample.csv` — 5,000 synthetic transactions (the
  `is_fraud` column is training-only; it's not part of what you serve)
- `models/fraud_xgb_v3.joblib` — the pre-trained model bundle

## Tasks

1. **(5 min)** Run `notebook_v1.ipynb` top to bottom. Note the three
   execution-order traps marked `# SMELL` — you'll be asked about them.
2. **(10 min)** Create the skeleton:
   - `pyproject.toml` (Python ≥3.12; deps: `pydantic`, `pandas`,
     `scikit-learn`, `joblib`)
   - `src/fraud_service/` with `domain/`, `service/`, `adapters/` subpackages
3. **(15 min)** Move code into layers, following the dependency rule from
   lecture (domain imports nothing from adapters or frameworks):
   - Entities + the feature-extraction logic → `domain/entities.py`
   - Threshold/decision logic → `domain/policies.py`
   - Scoring orchestration → `service/scorer.py`, depending on a `Model`
     protocol (not on sklearn directly)
   - joblib loading → `adapters/sklearn_model.py` — this should be the
     *only* file that imports `joblib`/`sklearn`
4. **(10 min)** Write `src/fraud_service/batch.py`: read
   `data/transactions_sample.csv`, score each row, write `scored.csv`. Wire
   the concrete model class together with the scorer **only** in this file.
5. **(5 min)** Add `Makefile` targets `install`, `run-batch`, `lint` (ruff).
   Run `make run-batch` (or the equivalent commands directly — see the
   repo's `README.md` if `make` isn't on your machine).
6. **(5 min)** Commit: `refactor: extract clean architecture layers from notebook`

## Definition of done

- `make run-batch` loads the model, scores all 5,000 transactions, and
  writes `scored.csv` with block/review/allow counts.
- `ruff check src tests` passes clean.
- Nothing outside `adapters/` imports `sklearn` or `joblib`.
- `python -m fraud_service.batch` can be re-run from a clean checkout after
  `pip install -e .`, with no manual steps beyond that.

## Stuck?

Talk to your pair, then flag your instructor rather than skipping ahead —
your instructor will build the tricky part live with you instead of just
handing you the answer.
