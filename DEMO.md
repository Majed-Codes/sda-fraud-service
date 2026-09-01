# Demo script — 5 minutes

Clone to running, one valid request, one rejected, a behavioural test, the CI
story. Rehearse once; the timings below are from a real run.

## 0. Before the room arrives

```bash
docker compose down -v          # start from nothing, visibly
docker image rm fraud-service:slim
```

## 1. Clone to running (90s)

```bash
git clone https://github.com/Majed-Codes/sda-fraud-service && cd sda-fraud-service
make up
```

Say while it builds: dependencies install in the builder stage and are cached;
only the app wheel and the model cross into the runtime image.

```bash
docker compose ps
```

Point at both services `healthy`, not `running` — the API's healthcheck is gated
on Redis reporting healthy first.

## 2. A valid request (45s)

```bash
curl -s localhost:8080/v1/predict -H 'content-type: application/json' \
     -d @payloads/sample.json | jq
```

`0.557066`, `allow`, `v3.2.0`, and a trace id that also appears in
`X-Trace-Id` and in every log line for that request.

```bash
docker compose logs api --tail 3 | jq -c 'select(.event=="prediction_served")'
```

Note what is absent: no `customer_id`, no `amount`, and the probability bucketed
to 0.1 steps.

## 3. A rejected request (30s)

```bash
curl -s -X POST localhost:8080/v1/predict -H 'content-type: application/json' \
     -d @payloads/malformed/transaction_id_whitespace.json | jq
```

422, one envelope shape, the field named, the value never echoed back. Then:

```bash
pytest tests/integration/test_malformed_corpus.py -q
```

51 malformed files, all rejected; 20 valid files, all accepted. Both directions,
so the tightening cannot overshoot.

## 4. A behavioural test (45s)

```bash
pytest tests/behavioural -q
```

The one to talk about is the golden file: 5000 recorded scores, re-scored
through the serving path, matched to 1e-9. That is the training/serving skew
tripwire — the notebook's original defect was computing `amount_log` a second
way, and this is what would catch it.

## 5. The CI story (60s)

Open the Actions tab on the latest green run.

- `lint`, `test` and `secrets` start together — no `needs:` between them.
- `image-smoke` waits for all three, then builds once and runs the image.
- `publish` runs only on push to `main`. Never on a pull request: a fork PR
  executes untrusted code, and that context must not hold registry credentials.
- The image is tagged with the commit SHA. Never `:latest`.

Then show the blocked PR: branch protection requires those checks, so a red one
cannot merge. A pipeline without protection is decoration.

## 6. Close

```bash
docker compose down
```

Numbers worth saying out loud: 437 MB image against a 500 MB budget, 15 s warm
rebuild, 1.0 s cold start, 226 tests, of which the 224 non-slow ones hold 100% branch coverage in 2.9 s.
Everything measured on this machine and written down in `BENCHMARKS.md`.
