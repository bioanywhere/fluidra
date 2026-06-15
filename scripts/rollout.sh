#!/usr/bin/env bash
# Staged traffic rollout for chat-api with auto-rollback on SLO breach
# (blueprint §11.4). Usage: ./scripts/rollout.sh <env> <percent>
set -euo pipefail

ENV="${1:?usage: rollout.sh <env> <percent>}"
PCT="${2:?usage: rollout.sh <env> <percent>}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-chat-api}"

echo "Routing ${PCT}% of ${SERVICE} traffic to the latest revision (${ENV})..."
gcloud run services update-traffic "${SERVICE}" \
  --region "${REGION}" \
  --to-revisions LATEST="${PCT}"

echo "Waiting 300s before SLO check..."
sleep 300

if ! ./scripts/check_slo.sh "${ENV}"; then
  echo "SLO breach — rolling back ${SERVICE} to the previous revision"
  gcloud run services update-traffic "${SERVICE}" \
    --region "${REGION}" --to-revisions LATEST=0
  exit 1
fi
echo "Rollout to ${PCT}% healthy."
