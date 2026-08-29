#!/usr/bin/env bash
# Deploy the $100 billing kill switch for AgentOS.
# Usage (from repo root):
#   export PROJECT_ID=your-project
#   export BILLING_ACCOUNT_ID=XXXXXX-XXXXXX-XXXXXX   # from: gcloud billing accounts list
#   export REGION=us-central1
#   bash scripts/gcp-killswitch/deploy.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
BILLING_ACCOUNT_ID="${BILLING_ACCOUNT_ID:?Set BILLING_ACCOUNT_ID (gcloud billing accounts list)}"
REGION="${REGION:-us-central1}"
TOPIC_ID="${TOPIC_ID:-agentos-billing-kill}"
FUNCTION_NAME="${FUNCTION_NAME:-agentos-stop-billing}"
BUDGET_AMOUNT="${BUDGET_AMOUNT:-100}"
KILL_AT_USD="${KILL_AT_USD:-100}"
SIMULATE_DEACTIVATION="${SIMULATE_DEACTIVATION:-false}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="${ROOT}/scripts/gcp-killswitch"

gcloud config set project "${PROJECT_ID}"

gcloud services enable \
  billingbudgets.googleapis.com \
  cloudbilling.googleapis.com \
  cloudbuild.googleapis.com \
  cloudfunctions.googleapis.com \
  eventarc.googleapis.com \
  run.googleapis.com \
  pubsub.googleapis.com \
  artifactregistry.googleapis.com \
  --project="${PROJECT_ID}"

gcloud pubsub topics create "${TOPIC_ID}" --project="${PROJECT_ID}" 2>/dev/null || true

gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --runtime=python312 \
  --region="${REGION}" \
  --source="${SRC}" \
  --entry-point=stop_billing \
  --trigger-topic="${TOPIC_ID}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},KILL_AT_USD=${KILL_AT_USD},SIMULATE_DEACTIVATION=${SIMULATE_DEACTIVATION}" \
  --project="${PROJECT_ID}" \
  --quiet

SA="$(gcloud functions describe "${FUNCTION_NAME}" --region="${REGION}" --gen2 \
  --format='value(serviceConfig.serviceAccountEmail)' --project="${PROJECT_ID}")"

echo "Function SA: ${SA}"
echo "Granting Cloud Run Admin on the project (scale services to 0)..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/run.admin" \
  --quiet

echo "Granting Billing Project Manager on the BILLING ACCOUNT (unlink project)..."
gcloud billing accounts add-iam-policy-binding "${BILLING_ACCOUNT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/billing.projectManager" || {
    echo "Could not bind billing.projectManager. You must be Billing Account Administrator."
    echo "In Console: Billing → Account management → add ${SA} with Project Billing Manager."
  }

# Gross usage (before promo credits) so $100 of the $150 grant trips the switch.
gcloud billing budgets create \
  --billing-account="${BILLING_ACCOUNT_ID}" \
  --display-name="AgentOS kill at \$${BUDGET_AMOUNT}" \
  --budget-amount="${BUDGET_AMOUNT}" \
  --filter-projects="projects/${PROJECT_ID}" \
  --credit-types-treatment=exclude-all-credits \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100 \
  --notifications-rule-pubsub-topic="projects/${PROJECT_ID}/topics/${TOPIC_ID}" \
  --notifications-rule-monitoring-notification-channels="" \
  2>/dev/null || echo "Create the budget in Console if this command failed (Billing → Budgets)."

echo
echo "Kill switch deployed."
echo "Dry-run test (does not unlink if SIMULATE_DEACTIVATION=true):"
echo "  gcloud pubsub topics publish ${TOPIC_ID} --project=${PROJECT_ID} --message='{\"costAmount\":100.01,\"budgetAmount\":100}'"
echo "Then: gcloud functions logs read ${FUNCTION_NAME} --region=${REGION} --gen2 --limit=20"
echo
echo "When logs look correct, redeploy with SIMULATE_DEACTIVATION=false (this script default)."
