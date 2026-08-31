# Lab 2 — Environment Setup

Do this before starting the tasks in `LAB2.md`.

## 1. Continue from Lab 1

Stay on `main` — you're continuing directly from the commit you made at
the end of Lab 1. No checkout needed.

## 2. Activate your venv

Reuse the same `.venv` from Lab 1 — don't create a new one.

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

## 3. Install dependencies

`pyproject.toml` now has a `[build-system]` section (from your Lab 1 work),
so an editable install works:

```bash
pip install -e .
pip install "fastapi[standard]" uvicorn httpx
```

Part B (load testing) also needs `hey`, which isn't a Python package:
- Windows: `choco install hey` (or download the binary from its GitHub releases)
- macOS: `brew install hey`
- Linux: download the binary from the `hey` GitHub releases page

## 4. Verify

```bash
fastapi dev src/fraud_service/api/app.py
```
In another terminal (with the venv activated):
```bash
curl http://localhost:8000/v1/health
```
You should get back a JSON `{"status": "ok", ...}` response.

## Common gotcha

If you're switching between multiple checkouts of this repo (e.g. a
practice folder and a solution folder), `pip install -e .` points your venv
at whichever folder you last ran it from — running a server from a
*different* folder without re-running `pip install -e .` there will
silently execute the wrong code with no error. If something behaves
unexpectedly after switching folders, re-run `pip install -e .` in the
folder you're actually working in.
