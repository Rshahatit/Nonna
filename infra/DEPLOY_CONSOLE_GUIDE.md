# Nonna — Google Cloud Console Deployment Guide

Deploy Nonna entirely through the Google Cloud Console UI. No CLI required.

---

## Step 1: Create or Select a GCP Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top bar
3. Click **New Project**
   - Project name: `nonna` (or any name)
   - Note your **Project ID** (e.g., `nonna-12345`) — you'll need it throughout
4. Select the new project from the dropdown

---

## Step 2: Enable Billing

1. Go to **Billing** in the left sidebar (or search "Billing")
2. Link a billing account to the project
3. Confirm billing is active

---

## Step 3: Enable APIs

Go to **APIs & Services → Library** (or search "API Library"). Search for and **Enable** each of these:

- [x] Cloud Run Admin API
- [x] Cloud Firestore API
- [x] Cloud Storage API (usually enabled by default)
- [x] Cloud Tasks API
- [x] Cloud Scheduler API
- [x] Cloud Text-to-Speech API
- [x] Vertex AI API
- [x] Artifact Registry API
- [x] Cloud Build API
- [x] Firebase Authentication API (Identity Toolkit)

For each one: search the name → click the result → click **Enable**.

---

## Step 4: Create Firestore Database

1. Go to **Firestore** in the left sidebar (or search "Firestore")
2. Click **Create Database**
3. Select **Native mode**
4. Choose location: **us-central1** (recommended for Vertex AI availability)
5. Click **Create**

---

## Step 5: Create Cloud Storage Bucket

1. Go to **Cloud Storage → Buckets**
2. Click **Create**
3. Bucket name: `{your-project-id}-nonna-media` (e.g., `nonna-12345-nonna-media`)
4. Location type: **Region** → **us-central1**
5. Storage class: **Standard**
6. Access control: **Uniform**
7. Click **Create**

### Set CORS (required for frontend media access)

This one step does require the CLI or Cloud Shell:

1. Click the **Activate Cloud Shell** button (terminal icon, top-right of console)
2. In Cloud Shell, run:
   ```bash
   cat > /tmp/cors.json << 'EOF'
   [{"origin": ["*"], "method": ["GET", "HEAD"], "responseHeader": ["Content-Type"], "maxAgeSeconds": 3600}]
   EOF
   gsutil cors set /tmp/cors.json gs://YOUR-BUCKET-NAME
   ```
   Replace `YOUR-BUCKET-NAME` with your actual bucket name.

---

## Step 6: Create Artifact Registry Repository

1. Go to **Artifact Registry** (search it)
2. Click **Create Repository**
3. Name: `nonna`
4. Format: **Docker**
5. Mode: **Standard**
6. Region: **us-central1**
7. Click **Create**

---

## Step 7: Build & Push Backend Image via Cloud Build

You can build Docker images directly from the console using Cloud Build.

1. Go to **Cloud Build → Triggers**
2. Or easier: use **Cloud Shell** (top-right terminal icon):
   ```bash
   # Clone your repo (or upload code)
   git clone https://github.com/YOUR_USERNAME/Nonna.git
   cd Nonna

   # Build backend
   gcloud builds submit ./backend \
     --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/nonna/nonna-backend:latest

   # Build frontend (replace BACKEND_URL after deploying backend)
   gcloud builds submit ./frontend \
     --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/nonna/nonna-frontend:latest
   ```

Alternatively, build locally and push:
   ```bash
   docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/nonna/nonna-backend:latest ./backend
   docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/nonna/nonna-backend:latest
   ```

---

## Step 8: Deploy Backend to Cloud Run

1. Go to **Cloud Run**
2. Click **Create Service**
3. Select **Deploy one revision from an existing container image**
4. Click **Select** → navigate to your Artifact Registry image:
   `us-central1-docker.pkg.dev/{project-id}/nonna/nonna-backend:latest`
5. Service name: `nonna-backend`
6. Region: **us-central1**

### Configure settings:

**Container tab:**
- Container port: `8000`
- Memory: `4 GiB`
- CPU: `2`
- Request timeout: `3600` seconds
- Maximum concurrent requests: `80`

**Environment variables** (click "Add Variable" for each):

| Variable | Value |
|----------|-------|
| `GOOGLE_CLOUD_PROJECT` | your-project-id |
| `GEMINI_API_KEY` | your Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GCS_BUCKET_MEDIA` | {project-id}-nonna-media |
| `GCS_BUCKET_TRANSCRIPTS` | {project-id}-nonna-media |
| `GCS_BUCKET_REELS` | {project-id}-nonna-media |
| `FIREBASE_PROJECT_ID` | your-project-id |
| `TWILIO_ACCOUNT_SID` | from [twilio.com/console](https://www.twilio.com/console) |
| `TWILIO_AUTH_TOKEN` | from Twilio console |
| `TWILIO_PHONE_NUMBER` | your Twilio number (+1...) |
| `SENDGRID_API_KEY` | from [sendgrid.com](https://sendgrid.com) (optional) |
| `USE_LOCAL_STORAGE` | `false` |

**Autoscaling tab:**
- Minimum instances: `0`
- Maximum instances: `10`

**Networking tab:**
- HTTP/2: **Enable** (required for WebSocket support)

**Authentication:**
- Select **Allow unauthenticated invocations**

8. Click **Create**
9. Wait for deployment — copy the **Service URL** (e.g., `https://nonna-backend-xxxxx.run.app`)

### Update CORS env var:

1. Click into the `nonna-backend` service
2. Click **Edit & Deploy New Revision**
3. Add environment variables:
   - `BACKEND_URL` = the service URL you just copied
   - `NEXT_PUBLIC_APP_URL` = (leave blank for now, update after frontend deploy)
4. Click **Deploy**

---

## Step 9: Deploy Frontend to Cloud Run

First, rebuild the frontend with the backend URL baked in.

In **Cloud Shell**:
```bash
cd Nonna

# Build with the backend URL
gcloud builds submit ./frontend \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/nonna/nonna-frontend:latest \
  --substitutions=_NEXT_PUBLIC_BACKEND_URL=https://nonna-backend-xxxxx.run.app
```

Or if your Dockerfile uses build args, build locally:
```bash
docker build \
  --build-arg NEXT_PUBLIC_BACKEND_URL=https://nonna-backend-xxxxx.run.app \
  --build-arg NEXT_PUBLIC_APP_URL=https://placeholder.run.app \
  -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/nonna/nonna-frontend:latest \
  ./frontend
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/nonna/nonna-frontend:latest
```

Then in Cloud Run:

1. Go to **Cloud Run** → **Create Service**
2. Select your frontend image from Artifact Registry
3. Service name: `nonna-frontend`
4. Region: **us-central1**

### Configure:
- Container port: `3000`
- Memory: `512 MiB`
- CPU: `1`
- Min instances: `0`, Max: `5`
- **Allow unauthenticated invocations**
- Click **Create**

5. Copy the **Frontend Service URL**

### Update backend CORS:

1. Go back to `nonna-backend` in Cloud Run
2. **Edit & Deploy New Revision**
3. Update `NEXT_PUBLIC_APP_URL` to the frontend URL
4. Click **Deploy**

---

## Step 10: Create Cloud Tasks Queue

1. Go to **Cloud Tasks** (search it)
2. Click **Create Queue**
3. Queue ID: `reel-generation`
4. Region: **us-central1**
5. Max dispatches per second: `5`
6. Max concurrent dispatches: `3`
7. Max attempts: `3`
8. Min backoff: `10s`
9. Max backoff: `300s`
10. Click **Create**

---

## Step 11: Create Cloud Scheduler Jobs

1. Go to **Cloud Scheduler** (search it)
2. Click **Create Job**

### Job 1: Call Scheduler
- Name: `nonna-call-scheduler`
- Region: **us-central1**
- Frequency: `*/15 * * * *` (every 15 minutes)
- Timezone: **UTC**
- Target type: **HTTP**
- URL: `https://nonna-backend-xxxxx.run.app/internal/check-schedule`
- HTTP method: **POST**
- Auth header: **Add OIDC token**
  - Service account: `{project-id}@appspot.gserviceaccount.com`
- Click **Create**

### Job 2: Weekly Digest
- Name: `nonna-weekly-digest`
- Frequency: `0 10 * * 0` (Sundays at 10am UTC)
- Same configuration as above but URL: `https://nonna-backend-xxxxx.run.app/internal/weekly-digest`

---

## Step 12: Firebase Auth Setup

1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. Click **Add Project** → select your existing GCP project → Continue through the steps
3. Go to **Authentication** (left sidebar)
4. Click **Get Started**
5. Click **Sign-in method** tab
6. Click **Google** → **Enable** → set a support email → **Save**
7. Go to **Settings** tab → **Authorized domains**
   - Add your frontend Cloud Run domain (without `https://`)
   - e.g., `nonna-frontend-xxxxx.run.app`
8. Go to **Project Settings** (gear icon, top-left)
   - Scroll to **Your apps** → click **Web** (</> icon)
   - Register an app (name: `nonna-web`)
   - Copy the config values:
     - `apiKey` → use as `NEXT_PUBLIC_FIREBASE_API_KEY`
     - `authDomain` → use as `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
     - `projectId` → use as `NEXT_PUBLIC_FIREBASE_PROJECT_ID`

If you need these baked into the frontend, rebuild the frontend image with these build args and redeploy.

---

## Step 13: Configure Twilio Webhooks

1. Go to [twilio.com/console](https://www.twilio.com/console)
2. Navigate to **Phone Numbers → Manage → Active Numbers**
3. Click your phone number
4. Under **Voice Configuration**:
   - "A call comes in" webhook URL: `https://nonna-backend-xxxxx.run.app/twilio/voice`
   - HTTP method: **POST**
   - "Call status changes" URL: `https://nonna-backend-xxxxx.run.app/twilio/status`
   - HTTP method: **POST**
5. Click **Save Configuration**

---

## Step 14: Verify Deployment

### Health check
Open in browser: `https://nonna-backend-xxxxx.run.app/health`
Expected: `{"status": "healthy", "service": "nonna-api", "version": "0.2.0"}`

### API docs
Open: `https://nonna-backend-xxxxx.run.app/docs`

### Frontend
Open: `https://nonna-frontend-xxxxx.run.app`

### Full test
1. Create an elder via the setup page
2. Trigger a phone call
3. Have a 2-minute conversation
4. Check the archive for the Memory Reel
5. Try the PWA talk page with camera

---

## Troubleshooting

| Issue | Where to Check | Fix |
|-------|---------------|-----|
| WebSocket 502 errors | Cloud Run → nonna-backend → Logs | Ensure HTTP/2 is enabled on the service |
| Twilio calls fail | Twilio Console → Monitor → Logs | Check webhook URL is correct and backend is responding |
| CORS errors in browser | Browser DevTools → Console | Update `NEXT_PUBLIC_APP_URL` env var on backend to match frontend URL |
| Firestore permission denied | Cloud Run → nonna-backend → Logs | Cloud Run service account needs Firestore User role (IAM) |
| Imagen 3 / Vertex AI errors | Cloud Run → Logs | Verify Vertex AI API is enabled; service account needs Vertex AI User role |
| FFmpeg errors in reel pipeline | Cloud Run → Logs | FFmpeg should be in the Docker image; check Dockerfile |
| Firebase Auth redirect fails | Browser → Network tab | Add frontend domain to Firebase authorized domains |
| Cloud Tasks not executing | Cloud Tasks → Queue → Tasks tab | Check service account has Cloud Run Invoker role |

### Checking Logs

1. Go to **Cloud Run** → click service name
2. Click **Logs** tab
3. Filter by severity to find errors

### IAM Roles

If you get permission errors, go to **IAM & Admin → IAM** and ensure the Cloud Run service account has:
- Cloud Datastore User (Firestore)
- Storage Object Admin (Cloud Storage)
- Cloud Tasks Enqueuer
- Vertex AI User
- Cloud Run Invoker (for Cloud Tasks/Scheduler callbacks)

---

## Redeployment After Code Changes

1. Rebuild the image (Cloud Shell or local):
   ```bash
   gcloud builds submit ./backend \
     --tag us-central1-docker.pkg.dev/PROJECT_ID/nonna/nonna-backend:latest
   ```
2. Go to **Cloud Run** → `nonna-backend` → **Edit & Deploy New Revision**
3. The image tag is `latest`, so just click **Deploy** (it pulls the new image)

Same process for frontend.

---

## Cost Estimate

With minimal usage (a few calls per day, scale-to-zero):
- Cloud Run: ~$0 (free tier covers light usage)
- Firestore: ~$0 (free tier: 1 GiB storage, 50K reads/day)
- Cloud Storage: ~$0.02/GB/month
- Vertex AI (Imagen 3): ~$0.04/image
- Cloud TTS: ~$4/1M characters
- Gemini API: usage-based (see [pricing](https://ai.google.dev/pricing))
- Twilio: ~$0.014/min for calls + $1/mo per number

Total for light demo usage: **under $5/month** (excluding Twilio)
