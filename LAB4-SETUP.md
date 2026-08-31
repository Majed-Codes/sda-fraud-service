# Lab 4 — Environment Setup

Do this before starting the tasks in `LAB4.md`.

## 1. Continue from Lab 3

Stay on `main`, continuing from your Lab 3 commit. No checkout needed.

## 2. Activate your venv

Same `.venv` as before.

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

## 3. Install dependencies

This lab needs `pytest`, `pytest-cov` and `httpx`, which haven't come up
yet:

```bash
pip install pytest pytest-cov httpx
```

## 4. Verify

```bash
pytest --collect-only
```
should run without error and report no tests collected — that's expected
before you've written any. It just confirms `pytest` and your editable
install both work.

## Docker note

Docker isn't needed for this lab (it's about the test suite, not the
container), but keep it running if you still have Lab 3's `docker compose`
stack up — no need to tear it down.
