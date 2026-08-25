#!/usr/bin/env bash
set -e

# AgentOS Cloud Run Deployment Script
# 
# Requires:
# 1. gcloud CLI installed and authenticated (gcloud auth login)
# 2. A GCP project with billing enabled
# 3. Environment variables: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_REGION

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set."
  exit 1
fi

if [ -z "$GOOGLE_CLOUD_REGION" ]; then
  export GOOGLE_CLOUD_REGION="us-central1"
  echo "Warning: GOOGLE_CLOUD_REGION not set, defaulting to $GOOGLE_CLOUD_REGION"
fi

echo "=========================================================="
echo " Deploying AgentOS to Google Cloud Run"
echo " Project: $GOOGLE_CLOUD_PROJECT"
echo " Region:  $GOOGLE_CLOUD_REGION"
echo "=========================================================="

# Ensure APIs are enabled
echo "==> Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    firestore.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    --project=$GOOGLE_CLOUD_PROJECT

# 1. Build and Deploy Backend (API)
echo "==> Deploying backend API..."
gcloud run deploy agentos-api \
    --source . \
    --platform managed \
    --region $GOOGLE_CLOUD_REGION \
    --allow-unauthenticated \
    --set-env-vars="STORAGE_BACKEND=firestore,APP_ENV=production,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT" \
    --project=$GOOGLE_CLOUD_PROJECT

# Get Backend URL
API_URL=$(gcloud run services describe agentos-api --platform managed --region $GOOGLE_CLOUD_REGION --format 'value(status.url)' --project=$GOOGLE_CLOUD_PROJECT)
echo "✅ Backend API deployed at: $API_URL"

# 2. Build and Deploy Frontend
echo "==> Deploying Next.js frontend..."
# Ensure frontend uses standalone output for Cloud Run
sed -i.bak 's/output: "export"/output: "standalone"/g' frontend/next.config.js || true

gcloud run deploy agentos-frontend \
    --source ./frontend \
    --platform managed \
    --region $GOOGLE_CLOUD_REGION \
    --allow-unauthenticated \
    --set-env-vars="NEXT_PUBLIC_API_URL=$API_URL" \
    --project=$GOOGLE_CLOUD_PROJECT

FRONTEND_URL=$(gcloud run services describe agentos-frontend --platform managed --region $GOOGLE_CLOUD_REGION --format 'value(status.url)' --project=$GOOGLE_CLOUD_PROJECT)
echo "✅ Frontend deployed at: $FRONTEND_URL"

echo "=========================================================="
echo " Deployment Complete!"
echo " "
echo " 1. Access the app: $FRONTEND_URL"
echo " 2. Add $API_URL to your Google OAuth 'Authorized JavaScript origins'"
echo " 3. Add $FRONTEND_URL/auth/callback to 'Authorized redirect URIs'"
echo " 4. Add your secrets to GCP Secret Manager:"
echo "    - GEMINI_API_KEY"
echo "    - GOOGLE_OAUTH_CLIENT_ID"
echo "    - GOOGLE_OAUTH_CLIENT_SECRET"
echo "=========================================================="
