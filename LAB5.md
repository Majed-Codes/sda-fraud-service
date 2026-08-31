# Lab 5 — Build the Pipeline

**Duration:** 50 minutes · **Pairs**
Setup: continue from your Lab 4 commit — see `LAB5-SETUP.md`. You'll need
a **personal GitHub repository** for this lab: create an empty one on your
own account, then re-point your local clone at it:

```bash
git remote set-url origin <your-new-empty-repo-url>
git push -u origin --all
```

(GitHub Actions and GitHub Container Registry both need to run under an
account you actually control — that's why this isn't done against the
shared course repo.)

## Objective

A working `.github/workflows/ci.yml` on your own repo: lint and test run in
parallel, a container gets built and smoke-tested, and — only on `main` —
the image gets pushed to your GHCR.

## Tasks

1. **(10 min)** Add a `lint` job (ruff, import-linter, mypy — all covered
   in this morning's lecture) and a `test` job (the fast suite from Lab 4).
   Push, watch it run in the Actions tab. If dependency installation fails,
   check what's actually being installed versus what your `pyproject.toml`
   declares.
2. **(15 min)** Add an `image-smoke` job that builds the Docker image,
   loads it locally, runs it, and hits `/v1/ready` and `/v1/predict` before
   the job is allowed to pass. Push again; compare the timing of this run
   against the first — caching should make a real difference the second
   time you touch this job.
3. **(15 min)** Add a `publish` job, gated so it only runs on pushes to
   `main` (never on pull requests — ask yourself why that matters before
   checking the answer with your instructor). Merge to `main`, confirm the
   image lands in your GHCR, then `docker pull` it and smoke-test the
   *pulled* image.
4. **(10 min)** Turn on branch protection for `main`: require your `lint`,
   `test`, and `image-smoke` checks to pass before merging. Your instructor
   will demo what happens when a PR can't pass those checks — watch for
   what actually gets blocked and why.

## Definition of done

- A PR against your `main` shows lint and test running in parallel, not
  sequentially.
- The image in your GHCR is tagged with a git SHA, never `:latest`.
- Branch protection actually blocks a merge when a required check is red —
  don't just enable it and assume it works, prove it.

## Stuck?

Talk to your pair, then flag your instructor rather than skipping ahead.
