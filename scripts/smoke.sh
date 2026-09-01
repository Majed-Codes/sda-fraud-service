#!/usr/bin/env bash
# Smoke-test a built image the way production runs it: detached, published
# port, no source mounted. Exits non-zero on the first failed assertion.
#
# usage: scripts/smoke.sh [IMAGE] [HOST_PORT]
set -euo pipefail

IMAGE="${1:-fraud-service:slim}"
PORT="${2:-8199}"
CONTAINER="smoke-$$"
BASE="http://127.0.0.1:${PORT}"
DEADLINE=60

cleanup() {
  local status=$?
  if [ $status -ne 0 ]; then
    echo "--- container logs ---" >&2
    docker logs "$CONTAINER" 2>&1 | tail -50 >&2 || true
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  exit $status
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

# A listener already on this port silently shadows Docker's published port,
# and the test then asserts against the wrong process. Skip the check rather
# than fail it where lsof is absent.
if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "port $PORT is already in use; a squatting listener silently shadows the container"
  fi
fi

echo "starting $IMAGE as $CONTAINER on :$PORT"
docker run -d --name "$CONTAINER" -p "${PORT}:8000" "$IMAGE" >/dev/null

# Wait on the image's own HEALTHCHECK. If it has none, fall back to polling
# readiness directly - but say so, because an unhealthchecked image in
# production has nothing for an orchestrator to gate on.
has_health=$(docker inspect -f '{{if .State.Health}}yes{{else}}no{{end}}' "$CONTAINER")
[ "$has_health" = yes ] || echo "warning: image declares no HEALTHCHECK, polling /v1/ready instead" >&2

started=$(date +%s)
while :; do
  if [ "$has_health" = yes ]; then
    state=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER")
    [ "$state" = healthy ] && break
    [ "$state" = unhealthy ] && fail "healthcheck went unhealthy"
  else
    curl -fsS "$BASE/v1/ready" >/dev/null 2>&1 && break
  fi
  running=$(docker inspect -f '{{.State.Running}}' "$CONTAINER")
  [ "$running" = true ] || fail "container exited before becoming ready"
  [ $(( $(date +%s) - started )) -ge $DEADLINE ] && fail "not ready within ${DEADLINE}s"
  sleep 0.5
done
echo "ready in $(( $(date +%s) - started ))s"

# 1. Liveness and readiness answer.
[ "$(curl -fsS "$BASE/v1/health")" = '{"status":"ok"}' ] || fail "/v1/health wrong body"
[ "$(curl -fsS "$BASE/v1/ready")" = '{"status":"ready"}' ] || fail "/v1/ready wrong body"

# 2. A real prediction, asserted on the body - a 200 alone proves nothing.
body=$(curl -fsS -X POST "$BASE/v1/predict" \
  -H 'content-type: application/json' -d @payloads/sample.json)
echo "$body" | grep -q '"decision":"allow"' || fail "unexpected decision: $body"
echo "$body" | grep -q '"model_version":"v3.2.0"' || fail "unexpected model version: $body"
echo "$body" | grep -q '"fraud_probability":0.557066' || fail "score drifted: $body"

# 3. Validation still rejects - a container serving 200s to malformed input
#    is worse than one that is down.
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/predict" \
  -H 'content-type: application/json' -d '{"transaction_id":"x"}')
[ "$code" = 422 ] || fail "malformed payload returned $code, expected 422"

# 4. The image runs unprivileged.
user=$(docker exec "$CONTAINER" whoami)
[ "$user" != root ] || fail "container runs as root"

echo "PASS: $IMAGE ($user, ready in $(( $(date +%s) - started ))s)"
