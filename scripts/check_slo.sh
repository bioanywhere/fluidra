#!/usr/bin/env bash
# SLO check used during staged rollout (blueprint §11.4). Placeholder that wires
# to Cloud Monitoring; returns non-zero on breach so rollout.sh rolls back.
# Usage: ./scripts/check_slo.sh <env>
set -euo pipefail

ENV="${1:?usage: check_slo.sh <env>}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-chat-api}"

# TODO: query Cloud Monitoring for error-rate / p95 latency over the last window
# and fail if they breach the SLOs (p95 > 4s, error rate > 1%, any sev-1).
# Until wired, do a basic liveness check against the service URL.
URL=$(gcloud run services describe "${SERVICE}" --region "${REGION}" \
  --format='value(status.url)' 2>/dev/null || true)

if [ -z "${URL}" ]; then
  echo "check_slo: could not resolve ${SERVICE} URL"; exit 1
fi
code=$(curl -s -o /dev/null -w "%{http_code}" "${URL}/healthz")
if [ "${code}" != "200" ]; then
  echo "check_slo: ${SERVICE} unhealthy (${code})"; exit 1
fi
echo "check_slo: ${SERVICE} healthy (${ENV})"
