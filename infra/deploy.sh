#!/bin/bash
# Nonna — Google Cloud Deployment Script
# Usage: ./infra/deploy.sh <project-id> <region>

set -euo pipefail

PROJECT_ID="${1:?Usage: ./infra/deploy.sh <project-id> <region>}"
REGION="${2:-us-central1}"

echo "=== Deploying Nonna to project: $PROJECT_ID, region: $REGION ==="

# Enable required APIs
echo "Enabling Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  texttospeech.googleapis.com \
  aiplatform.googleapis.com \
  cloudtasks.googleapis.com \
  cloudscheduler.googleapis.com \
  --project="$PROJECT_ID"

# Create Firestore database (if not exists)
echo "Setting up Firestore..."
gcloud firestore databases create \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --type=firestore-native 2>/dev/null || echo "Firestore database already exists"

# Create Cloud Storage buckets
echo "Creating storage buckets..."
for BUCKET in nonna-transcripts nonna-media nonna-reels; do
  gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${PROJECT_ID}-${BUCKET}" 2>/dev/null || \
    echo "Bucket ${PROJECT_ID}-${BUCKET} already exists"
done

# Create Cloud Tasks queue
echo "Creating Cloud Tasks queue..."
gcloud tasks queues create nonna-reel-pipeline \
  --location="$REGION" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Queue already exists"

# Build and deploy backend
echo "Building and deploying backend..."
gcloud builds submit ./backend \
  --tag "gcr.io/$PROJECT_ID/nonna-backend" \
  --project="$PROJECT_ID"

gcloud run deploy nonna-backend \
  --image "gcr.io/$PROJECT_ID/nonna-backend" \
  --platform managed \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"

BACKEND_URL=$(gcloud run services describe nonna-backend \
  --region "$REGION" --project "$PROJECT_ID" \
  --format="value(status.url)")

echo "Backend deployed at: $BACKEND_URL"

# Build and deploy frontend
echo "Building and deploying frontend..."
gcloud builds submit ./frontend \
  --tag "gcr.io/$PROJECT_ID/nonna-frontend" \
  --project="$PROJECT_ID"

gcloud run deploy nonna-frontend \
  --image "gcr.io/$PROJECT_ID/nonna-frontend" \
  --platform managed \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars "NEXT_PUBLIC_BACKEND_URL=$BACKEND_URL"

FRONTEND_URL=$(gcloud run services describe nonna-frontend \
  --region "$REGION" --project "$PROJECT_ID" \
  --format="value(status.url)")

echo "Frontend deployed at: $FRONTEND_URL"

# Create Cloud Scheduler job for scheduled calls
echo "Setting up call scheduler..."
gcloud scheduler jobs create http nonna-scheduled-calls \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --schedule="*/15 * * * *" \
  --uri="$BACKEND_URL/twilio/check-schedule" \
  --http-method=POST \
  --oidc-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" 2>/dev/null || \
  echo "Scheduler job already exists"

echo ""
echo "=== Deployment Complete ==="
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
echo ""
echo "Next steps:"
echo "1. Set environment variables (Twilio, Gemini API keys) in Cloud Run"
echo "2. Point Twilio webhooks to $BACKEND_URL/twilio/voice"
echo "3. Share $FRONTEND_URL with your family!"
