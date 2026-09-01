# Incident: credentials committed in `configs/dev.env`

**Detected:** 2026-09-01, `gitleaks detect` during the Module 6 hardening pass.
**Scope:** a GitHub personal access token, an AWS access key pair, and a
registry token, in `configs/dev.env`.

## The order is the whole answer

**Step 1 — rotate and revoke, immediately.**
Revoke the GitHub PAT, deactivate the AWS key pair, and rotate the registry
token. Do this before touching git.

The reason is simple: the moment a secret reaches a remote, you must assume it
is copied. Forks, clones, CI caches, the GitHub Events API, and any scraper
watching public pushes all have it, and a `git push --force` reaches none of
them. GitHub also keeps unreferenced objects reachable by SHA on the original
repository until it garbage-collects, so the blob stays fetchable by anyone who
saw the commit id.

Purging history first inverts the priorities. It is the slow, coordinating,
interruptive step, and while it runs the live credential is still valid. The
secret's value is the access it grants, so kill the access first. Once the
credential is dead, the copies are worthless and the cleanup is hygiene rather
than an emergency.

**Step 2 — purge the history, then close the hole.**
Remove the blob from every reachable commit, force-push, and have collaborators
re-clone rather than merge:

```bash
git filter-repo --path configs/dev.env --invert-paths
git push --force --all && git push --force --tags
```

Then ask GitHub Support to garbage-collect unreferenced objects, since the blob
stays fetchable by SHA until they do. Finish by removing the cause, not just the
artefact: `.env` and `configs/*.env` are gitignored, `configs/dev.env.example`
carries the key names with empty values, and `gitleaks` runs in CI so the next
one fails a build instead of reaching a remote.

## What happened here

Nothing left this machine. The planted file was detected in the working tree and
removed before any commit, so there is no history to rewrite — step 2 was a
`rm`, and step 1 was unnecessary because the values were generated for the
drill and never granted access to anything.

Had they been real, the rotation in step 1 would still have come first.

## Verification

```
$ gitleaks detect --no-git --source .    # working tree
no leaks found
$ gitleaks detect --source .             # full history
no leaks found
```
