#!/usr/bin/env bash
# Deploy AgentOS API to Cloud Run from Cloud Shell.
# Usage:
#   export PROJECT_ID=agentos-devpost
#   bash scripts/gcp/deploy-api-cloudshell.sh
# Create Secret Manager secrets first (this script does not create them):
#   secrets-master-key, jwt-private-key, jwt-public-key
# Do not set GEMINI_API_KEY. Vertex uses the Cloud Run service account.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "Set PROJECT_ID first:  export PROJECT_ID=agentos-devpost"
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
  firestore.googleapis.com \
  --project="${PROJECT_ID}"

# Production: Firestore + Vertex (ADC). Secrets must already exist in Secret Manager.
# CORS_ALLOWED_ORIGINS is set after the frontend URL is known (see docs/deploy-gcp.md).
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
  --set-env-vars="APP_ENV=production,STORAGE_BACKEND=firestore,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},GEMINI_MODEL=gemini-3.6-flash" \
  --set-secrets="SECRETS_MASTER_KEY=secrets-master-key:latest,JWT_PRIVATE_KEY=jwt-private-key:latest,JWT_PUBLIC_KEY=jwt-public-key:latest" \
  --quiet

URL="$(gcloud run services describe "${SERVICE}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
echo
echo "Deployed: ${URL}"
echo "Health:   ${URL}/health"
echo "Expect storage=firestore and llm=vertex. Do not set GEMINI_API_KEY."
echo "Grant roles/aiplatform.user and roles/datastore.user to the Cloud Run SA if Vertex or Firestore calls fail."
echo "After the frontend is deployed, set FRONTEND_BASE_URL and CORS_ALLOWED_ORIGINS (see docs/deploy-gcp.md)."
