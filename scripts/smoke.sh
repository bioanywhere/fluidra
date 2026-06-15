#!/usr/bin/env bash
# Smoke test a deployed environment: /healthz must be 200 and report db ok.
# Usage: ./scripts/smoke.sh <base_url>
set -euo pipefail

BASE_URL="${1:?usage: smoke.sh <base_url>}"

echo "Smoke-testing ${BASE_URL} ..."
code=$(curl -s -o /tmp/healthz.json -w "%{http_code}" "${BASE_URL}/healthz")
cat /tmp/healthz.json; echo
if [ "${code}" != "200" ]; then
  echo "FAIL: /healthz returned ${code}"
  exit 1
fi
if ! grep -q '"status":"ok"' /tmp/healthz.json; then
  echo "FAIL: /healthz did not report status ok"
  exit 1
fi
echo "OK: ${BASE_URL} is healthy"
