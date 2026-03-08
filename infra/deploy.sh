#!/bin/bash
# Nonna — Google Cloud Deployment Script
#
# Deploys the full Nonna stack to Google Cloud:
#   - Firestore (Native mode)
#   - Cloud Storage bucket
#   - Artifact Registry
#   - Cloud Run (backend + frontend)
#   - Cloud Tasks queue
#   - Cloud Scheduler jobs
#
# Usage:
#   ./infra/deploy.sh <project-id> [region]
#
# Environment variables (set before running or pass via .env):
#   GEMINI_API_KEY         — Google AI Studio API key
#   TWILIO_ACCOUNT_SID     — Twilio account SID
#   TWILIO_AUTH_TOKEN       — Twilio auth token
#   TWILIO_PHONE_NUMBER     — Twilio phone number (+1...)
#   SENDGRID_API_KEY        — SendGrid API key (optional)
#   FIREBASE_API_KEY        — Firebase web API key
#   FIREBASE_AUTH_DOMAIN    — Firebase auth domain
#
# The script is idempotent — safe to run multiple times.

set -euo pipefail

PROJECT_ID="${1:?Usage: ./infra/deploy.sh <project-id> [region]}"
REGION="${2:-us-central1}"
BUCKET="${PROJECT_ID}-nonna-media"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/nonna"

# Load .env if present
if [ -f .env ]; then
  echo "Loading .env file..."
  set -a; source .env; set +a
fi

echo ""
echo "============================================"
echo "  Deploying Nonna to Google Cloud"
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "============================================"
echo ""

# ─────────────── Step 1: APIs ───────────────

echo "[1/9] Enabling Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  texttospeech.googleapis.com \
  aiplatform.googleapis.com \
  cloudtasks.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  firebase.googleapis.com \
  identitytoolkit.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$PROJECT_ID"

# ─────────────── Step 2: Firestore ───────────────

echo "[2/9] Setting up Firestore (Native mode)..."
gcloud firestore databases create \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --type=firestore-native 2>/dev/null || echo "  Firestore database already exists"

# ─────────────── Step 3: Cloud Storage ───────────────

echo "[3/9] Creating Cloud Storage bucket..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET" 2>/dev/null || \
  echo "  Bucket $BUCKET already exists"

# Set CORS for frontend media access
cat > /tmp/nonna-cors.json << 'CORS_EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type", "Content-Range"],
    "maxAgeSeconds": 3600
  }
]
CORS_EOF
gsutil cors set /tmp/nonna-cors.json "gs://$BUCKET"
rm -f /tmp/nonna-cors.json

# ─────────────── Step 4: Artifact Registry ───────────────

echo "[4/9] Setting up Artifact Registry..."
gcloud artifacts repositories create nonna \
  --repository-format=docker \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --description="Nonna container images" 2>/dev/null || \
  echo "  Artifact Registry repo already exists"

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ─────────────── Step 5: Build + Deploy Backend ───────────────

echo "[5/9] Building backend image..."
BACKEND_IMAGE="${REGISTRY}/nonna-backend:latest"

docker build -t "$BACKEND_IMAGE" ./backend
docker push "$BACKEND_IMAGE"

echo "[6/9] Deploying backend to Cloud Run..."

# Build env vars string
ENV_VARS="GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
ENV_VARS="$ENV_VARS,GCS_BUCKET_MEDIA=$BUCKET"
ENV_VARS="$ENV_VARS,GCS_BUCKET_TRANSCRIPTS=$BUCKET"
ENV_VARS="$ENV_VARS,GCS_BUCKET_REELS=$BUCKET"
ENV_VARS="$ENV_VARS,FIREBASE_PROJECT_ID=$PROJECT_ID"
ENV_VARS="$ENV_VARS,USE_LOCAL_STORAGE=false"
[ -n "${GEMINI_API_KEY:-}" ]       && ENV_VARS="$ENV_VARS,GEMINI_API_KEY=$GEMINI_API_KEY"
[ -n "${TWILIO_ACCOUNT_SID:-}" ]   && ENV_VARS="$ENV_VARS,TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID"
[ -n "${TWILIO_AUTH_TOKEN:-}" ]    && ENV_VARS="$ENV_VARS,TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN"
[ -n "${TWILIO_PHONE_NUMBER:-}" ]  && ENV_VARS="$ENV_VARS,TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER"
[ -n "${SENDGRID_API_KEY:-}" ]     && ENV_VARS="$ENV_VARS,SENDGRID_API_KEY=$SENDGRID_API_KEY"

gcloud run deploy nonna-backend \
  --image "$BACKEND_IMAGE" \
  --platform managed \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10 \
  --use-http2 \
  --set-env-vars "$ENV_VARS"

BACKEND_URL=$(gcloud run services describe nonna-backend \
  --region "$REGION" --project "$PROJECT_ID" \
  --format="value(status.url)")

echo "  Backend: $BACKEND_URL"

# Update backend CORS with its own URL
gcloud run services update nonna-backend \
  --region "$REGION" --project "$PROJECT_ID" \
  --update-env-vars "BACKEND_URL=$BACKEND_URL" --quiet

# ─────────────── Step 7: Build + Deploy Frontend ───────────────

echo "[7/9] Building frontend image..."
FRONTEND_IMAGE="${REGISTRY}/nonna-frontend:latest"

docker build \
  --build-arg "NEXT_PUBLIC_BACKEND_URL=$BACKEND_URL" \
  --build-arg "NEXT_PUBLIC_APP_URL=https://placeholder.run.app" \
  ${FIREBASE_API_KEY:+--build-arg "NEXT_PUBLIC_FIREBASE_API_KEY=$FIREBASE_API_KEY"} \
  ${FIREBASE_AUTH_DOMAIN:+--build-arg "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=$FIREBASE_AUTH_DOMAIN"} \
  ${PROJECT_ID:+--build-arg "NEXT_PUBLIC_FIREBASE_PROJECT_ID=$PROJECT_ID"} \
  -t "$FRONTEND_IMAGE" ./frontend

docker push "$FRONTEND_IMAGE"

echo "[8/9] Deploying frontend to Cloud Run..."
gcloud run deploy nonna-frontend \
  --image "$FRONTEND_IMAGE" \
  --platform managed \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5

FRONTEND_URL=$(gcloud run services describe nonna-frontend \
  --region "$REGION" --project "$PROJECT_ID" \
  --format="value(status.url)")

echo "  Frontend: $FRONTEND_URL"

# Update backend CORS to include frontend URL
gcloud run services update nonna-backend \
  --region "$REGION" --project "$PROJECT_ID" \
  --update-env-vars "NEXT_PUBLIC_APP_URL=$FRONTEND_URL" --quiet

# ─────────────── Step 9: Cloud Tasks + Scheduler ───────────────

echo "[9/9] Setting up Cloud Tasks + Cloud Scheduler..."

# Cloud Tasks queue for async reel generation
gcloud tasks queues create reel-generation \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --max-dispatches-per-second=5 \
  --max-concurrent-dispatches=3 \
  --max-attempts=3 \
  --min-backoff=10s \
  --max-backoff=300s 2>/dev/null || echo "  Cloud Tasks queue already exists"

# Scheduler: check for scheduled calls every 15 minutes
SA_EMAIL="${PROJECT_ID}@appspot.gserviceaccount.com"

gcloud scheduler jobs create http nonna-call-scheduler \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --schedule="*/15 * * * *" \
  --uri="$BACKEND_URL/internal/check-schedule" \
  --http-method=POST \
  --oidc-service-account-email="$SA_EMAIL" 2>/dev/null || \
  echo "  Call scheduler job already exists"

# Scheduler: weekly family digest (Sundays 10am UTC)
gcloud scheduler jobs create http nonna-weekly-digest \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --schedule="0 10 * * 0" \
  --uri="$BACKEND_URL/internal/weekly-digest" \
  --http-method=POST \
  --oidc-service-account-email="$SA_EMAIL" 2>/dev/null || \
  echo "  Weekly digest job already exists"

# ─────────────── Done ───────────────

echo ""
echo "============================================"
echo "  Deployment Complete"
echo "============================================"
echo ""
echo "  Frontend:  $FRONTEND_URL"
echo "  Backend:   $BACKEND_URL"
echo "  API Docs:  $BACKEND_URL/docs"
echo ""
echo "  Verify:    curl $BACKEND_URL/health"
echo ""
echo "Remaining manual steps:"
echo "  1. Configure Twilio webhooks:"
echo "     Voice URL:    $BACKEND_URL/twilio/voice (POST)"
echo "     Status URL:   $BACKEND_URL/twilio/status (POST)"
echo ""
echo "  2. Configure Firebase Auth:"
echo "     - Enable Google Sign-In in Firebase Console"
echo "     - Add authorized domain: $(echo $FRONTEND_URL | sed 's|https://||')"
echo ""
echo "  3. Test it:"
echo "     - Open $FRONTEND_URL"
echo "     - Create an elder, trigger a call"
echo "     - Verify Memory Reel generates"
echo ""
