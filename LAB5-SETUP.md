# Lab 5 — Environment Setup

Do this before starting the tasks in `LAB5.md`.

## 1. Continue from Lab 4

Stay on `main`, continuing from your Lab 4 commit — no new local
dependencies for this lab.

## 2. Activate your venv

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

## 3. The part that actually matters this lab: your own GitHub repo

This lab's CI workflow needs to run under a GitHub account you control
(GitHub Actions and GHCR both need real permissions), so before touching
any code:

1. Create a new, empty repository on your own GitHub account.
2. Re-point your local clone at it:
   ```bash
   git remote set-url origin <your-new-empty-repo-url>
   git push -u origin --all
   git push -u origin --tags
   ```
3. Confirm it worked:
   ```bash
   git remote -v
   ```
   should show your own repo's URL, not the course repo.

## 4. Verify

```bash
pytest -m unit
```
should still pass, same as at the end of Lab 4. Nothing about the local
Python environment changes in this lab — it's entirely about the CI
pipeline.
