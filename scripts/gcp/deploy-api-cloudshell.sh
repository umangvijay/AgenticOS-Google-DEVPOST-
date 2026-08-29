#!/usr/bin/env bash
# Deploy AgentOS API to Cloud Run from Cloud Shell.
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   bash scripts/gcp/deploy-api-cloudshell.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "Set PROJECT_ID first:  export PROJECT_ID=your-project-id"
  exit 1
fi

REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-agentos-api}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${ROOT}"

echo "Project=${PROJECT_ID} Region=${REGION} Service=${SERVICE}"
gcloud config set project "${PROJECT_ID}"
gcloud config set builds/timeout 1800

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT_ID}"

# First deploy uses SQLite so the revision starts even if Firestore is not created yet.
gcloud run deploy "${SERVICE}" \
  --source="${ROOT}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=4 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --cpu-boost \
  --set-env-vars="APP_ENV=production,STORAGE_BACKEND=sqlite,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},GEMINI_MODEL=gemini-2.5-flash" \
  --quiet

URL="$(gcloud run services describe "${SERVICE}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
echo
echo "Deployed: ${URL}"
echo "Health:   ${URL}/health"
echo "If health is 200, Vertex + chat work after you grant roles/aiplatform.user to the Cloud Run SA."
echo "Then create Firestore and update STORAGE_BACKEND=firestore (see docs/deploy-gcp.md)."
