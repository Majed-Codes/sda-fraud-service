# Lab 3 — Environment Setup

Do this before starting the tasks in `LAB3.md`.

## 1. Continue from Lab 2

Stay on `main`, continuing from your Lab 2 commit. No checkout needed.

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

Nothing new to install for this lab — you're using the same editable
install from Lab 2 (`pip install -e .`). If you're picking this repo up
fresh (new machine, new clone), run that first.

## 4. Docker

This lab is about containerising the service, so you also need Docker
running:

```bash
docker run hello-world
```

If that doesn't print a success message, start Docker Desktop (or Colima
on macOS) before continuing — don't start the lab tasks until this works.

## 5. Verify

```bash
fastapi dev src/fraud_service/api/app.py
```
should still work exactly as in Lab 2 — this lab is about wrapping the
service in Docker, not changing the app code.
