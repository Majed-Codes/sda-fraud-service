# Engineering decisions

## 1. The model is baked into the image, not pulled at startup

`models/fraud_xgb_v3.joblib` is 3.6 KB and copied in at build time, so the image
is the complete unit of deployment: a SHA identifies both the code and the
weights that produced a score, and a rollback is one `docker run` away.

Pulling from object storage at startup would decouple retraining from releases,
which matters when weights are hundreds of megabytes and change more often than
code. It also adds a network dependency to readiness, a credential to manage,
and the possibility that two containers on the same SHA disagree. At this size
the coupling costs nothing and buys reproducibility, so baking wins. The
argument reverses the moment the artefact grows or retrains ship daily, and the
`COPY models` line is the only thing that changes.

## 2. The block threshold is configuration, not a constant or a model attribute

`block_threshold` is a `Settings` field, bounded 0.5–0.99, defaulting to 0.85.

It is not a constant in `policies.py`, because moving a risk threshold should
not require a release. It is not stored in the joblib bundle either, though that
is where it most wants to live: the threshold is a business decision owned by
risk, and the model artefact is owned by the data science pipeline. Putting it
in the bundle means a retrain silently changes blocking behaviour. Keeping it in
config makes the change auditable, reviewable and reversible without touching
either the model or the code. The bound is there because a fat-fingered `8.5`
would otherwise block nothing at all, silently.

## 3. Dependencies and the application are separate image layers

The builder installs `requirements.txt` into `/opt/venv` and separately emits a
wheel. The runtime stage copies the venv, then unpacks the wheel into it.

The obvious alternative — `pip install .` into the venv in the builder — is
shorter and was the first version. It makes the venv layer depend on source, so
every one-line edit re-copies ~290 MB into the runtime stage: measured, the warm
rebuild went from 15 s to 35 s. Splitting them keeps the heavy layer keyed only
on the lock file. The wheel is unpacked with `python -m zipfile` rather than
`pip install`, which also keeps pip out of the runtime image entirely.

## 4. Bytecode ships, even though deleting it would save 48 MB

`__pycache__` stays in the image.

Removing it is an attractive line in a size table and a disaster in practice:
with `PYTHONDONTWRITEBYTECODE=1` the interpreter recompiles numpy, scipy, pandas
and scikit-learn on every container start and can never cache the result. Cold
start went from **1.0 s to 32.3 s**. A 48 MB saving is worth roughly nothing;
thirty seconds of startup is the difference between a rolling deploy and an
outage. The budget was found elsewhere — stripped debug symbols, no `tests/`
directories, pip removed in the builder rather than the runtime stage.

## 5. Malformed input is rejected at the wire, not normalised

`transaction_id` and `customer_id` carry anchored ASCII patterns; whitespace-only
and whitespace-padded values are 422, not trimmed.

The permissive alternative is to strip and carry on, which is friendlier and
wrong here. `" CUST-0042 "` and `"CUST-0042"` are the same customer to a human
and two different strings to anything that joins on the field later; accepting
both means the service decides silently which one is canonical. Rejecting makes
the caller fix their serialisation once, at the boundary, while the error still
points at them. This came directly from evidence: 10 of the 51 malformed
payloads in `payloads/malformed/` were being scored successfully before the
patterns went in, including a NUL byte and a SQL fragment inside the length
bounds.

## 6. The healthcheck probes with Python, not curl

`HEALTHCHECK` runs `python -c "import urllib.request..."` against `/v1/ready`.

Installing `curl` is the conventional choice and appears in most reference
Dockerfiles. It also means an apt package in the runtime image that exists only
to make one HTTP request, when the interpreter already in the image can make it.
That is one less package to patch and one less thing for a scanner to report.
The trade is legibility — `curl -fsS` reads better than a line of inlined
Python — and a slightly slower probe, since it pays interpreter startup each
time. At a 5 s interval that is not a cost worth an extra package.
