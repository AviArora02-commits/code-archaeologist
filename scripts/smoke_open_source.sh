#!/usr/bin/env bash
# Smoke test for self-hosted open-source Cognee stack.
set -euo pipefail

API="${API:-http://localhost:8000/api}"

echo "==> Health"
curl -sf "$API/health" | tee /dev/stderr
echo

echo "==> Connect pallets/click (small Python repo)"
CONNECT=$(curl -sf -X POST "$API/repos/connect" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com/pallets/click"}')
echo "$CONNECT" | head -c 500
echo

REPO_ID=$(echo "$CONNECT" | python -c "import sys,json; print(json.load(sys.stdin)['repo_id'])")
JOB_ID=$(echo "$CONNECT" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

echo "==> Confirm ingest repo=$REPO_ID job=$JOB_ID"
curl -sf -X POST "$API/repos/$REPO_ID/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\",\"confirm\":true}" > /dev/null

echo "==> Waiting for ingest (local Cognee — may take several minutes)..."
for i in $(seq 1 120); do
  STATUS=$(curl -sf "$API/jobs/$JOB_ID")
  STATE=$(echo "$STATUS" | python -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
  echo "  [$i] status=$STATE"
  if [ "$STATE" = "completed" ]; then break; fi
  if [ "$STATE" = "failed" ]; then echo "$STATUS"; exit 1; fi
  sleep 10
done

echo "==> Trace query"
curl -sf -X POST "$API/query/why" \
  -H "Content-Type: application/json" \
  -d "{\"repo_id\":\"$REPO_ID\",\"query\":\"Why does the main CLI entry work this way?\"}" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('answer','')[:800])"

echo
echo "==> Open-source Cognee smoke test passed"
