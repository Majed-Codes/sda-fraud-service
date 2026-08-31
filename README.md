# fraud-service (SDA-AIE-113 golden-thread project)

We build this together, live, one lab at a time — this repo has no
pre-built solutions or checkpoint tags. Each lab's tasks are in `LABN.md`,
its environment setup in `LABN-SETUP.md`. Commit at the end of each lab so
your history shows the project growing lab by lab.

**Current state: pre-refactor.** `notebook_v1.ipynb` scores transactions using the
bundled model. It works, but it has the six classic notebook-to-production smells
covered in Module 1 - some are marked `# SMELL`, some aren't.

## Lab 1 — your task

Run the notebook top to bottom first and note the three execution-order traps.
Then extract it into a clean `src/fraud_service/` package: `domain/`, `service/`,
`adapters/`, wired together only in a new `src/fraud_service/batch.py` entrypoint.
See `LAB1.md` for the full task list
and expected output.

Data and model artefacts are already provided and stay constant across every lab:

- `data/transactions_sample.csv` — 5,000 synthetic transactions (with an `is_fraud`
  label — that column is training-only; it is not part of the serving contract).
- `models/fraud_xgb_v3.joblib` — pre-trained pipeline bundle: `{"pipeline": ..., "version": "v3.2.0"}`.
- `data/golden_scores_v3.csv` — this model's scores on the 5,000 rows, used from
  Module 4 onward as the skew tripwire.
