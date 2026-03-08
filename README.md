# Nonna

**A live conversational AI agent that helps elders preserve their stories, skills, and wisdom for their families.**

Nonna builds a genuine, ongoing relationship with elders through two parallel channels:
- **Phone calls** — zero friction, any phone. Nonna calls at scheduled times.
- **Vision-enabled PWA** — camera sees photos, objects, and surroundings to spark deeper stories.

After each conversation, Nonna transforms the stories into **Memory Reels**: short narrated videos with AI-generated illustrations that families keep forever.

## Architecture

```
Phone (Twilio) ──→ WebSocket ──→ Gemini Live API ──→ Memory Reel Pipeline
PWA (Browser)  ──→ WebSocket ──→ (+ Vision)        ├── Story Extraction (Gemini)
                                                     ├── Image Generation (Imagen 3)
                                                     ├── Narration (Cloud TTS)
                                                     └── Video Assembly (FFmpeg)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (PWA), React, Tailwind CSS |
| Backend | Python 3.12, FastAPI, uvicorn |
| Phone | Twilio Voice + Media Streams |
| AI Conversation | Gemini Live API (google-genai SDK) |
| Vision | Gemini 2.5 Pro (multimodal) |
| Story Extraction | Gemini 2.5 Pro |
| Image Generation | Imagen 3 (Vertex AI) |
| Narration | Google Cloud Text-to-Speech |
| Video Assembly | FFmpeg |
| Database | Google Cloud Firestore |
| File Storage | Google Cloud Storage |
| Hosting | Google Cloud Run |
| Task Queue | Google Cloud Tasks |
| Scheduling | Google Cloud Scheduler |

## Project Structure

```
nonna/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Environment configuration
│   │   ├── models/              # Pydantic data models
│   │   │   ├── elder.py         # Elder, Memory, Schedule models
│   │   │   └── session.py       # Session, Moment, Reel models
│   │   ├── routers/             # API endpoints
│   │   │   ├── elders.py        # Elder CRUD + call trigger
│   │   │   ├── sessions.py      # Session + Reel retrieval
│   │   │   ├── twilio_voice.py  # Twilio webhooks
│   │   │   ├── websocket_phone.py  # Phone audio streaming
│   │   │   └── websocket_pwa.py    # PWA audio + vision streaming
│   │   ├── services/            # Business logic
│   │   │   ├── conversation.py  # Gemini Live API engine
│   │   │   ├── firestore.py     # Data access layer
│   │   │   ├── memory_extraction.py  # Post-session memory update
│   │   │   ├── reel_pipeline.py # Full reel generation pipeline
│   │   │   ├── scheduling.py    # Outbound call scheduling
│   │   │   ├── notifications.py # Family SMS notifications
│   │   │   ├── storage.py       # Cloud Storage operations
│   │   │   └── twilio_service.py # Twilio voice integration
│   │   └── prompts/
│   │       └── nonna.py         # System prompt + personality
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Landing page
│   │   │   ├── setup/page.tsx   # Family setup flow
│   │   │   ├── talk/[elderId]/  # Elder conversation view
│   │   │   └── archive/[elderId]/ # Family archive view
│   │   ├── hooks/
│   │   │   └── useConversation.ts # WebSocket conversation hook
│   │   └── lib/
│   │       └── api.ts           # Backend API client
│   ├── Dockerfile
│   └── package.json
├── infra/
│   └── deploy.sh                # GCP deployment script
├── docker-compose.yml           # Local development
└── .env.example                 # Environment variables
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (optional — for containerized dev)

### Service Setup

Nonna depends on several external services. Below is how to set up each one. For **local-only testing** without real calls or media generation, only the Gemini API key is required — everything else can stay as defaults with in-memory storage enabled.

#### 1. Google Cloud Project

All GCP services (Firestore, Cloud Storage, TTS, Vertex AI, Cloud Tasks) live under one project.

1. Create a project at https://console.cloud.google.com
2. Enable billing
3. Enable the following APIs (search each in the API Library):
   - Cloud Firestore API
   - Cloud Storage API
   - Cloud Text-to-Speech API
   - Vertex AI API
   - Cloud Tasks API
   - Cloud Run API (for deployment)
4. Create a service account:
   - Go to **IAM & Admin → Service Accounts**
   - Create a new service account with roles: `Cloud Datastore User`, `Storage Admin`, `Cloud Tasks Enqueuer`
   - Download the JSON key file
5. Set in `.env`:
   ```
   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
   ```

#### 2. Gemini API Key

Used for real-time conversation (Gemini Live API), vision analysis, story extraction, and memory extraction.

1. Go to https://aistudio.google.com/apikey
2. Create an API key
3. Set in `.env`:
   ```
   GEMINI_API_KEY=your-gemini-api-key
   ```

#### 3. Twilio (Phone Calls)

Required only if you want phone call functionality. Not needed for PWA-only testing.

1. Create an account at https://www.twilio.com
2. Get a phone number with Voice capabilities
3. In your Twilio Console, find your Account SID and Auth Token
4. Configure the phone number's webhook:
   - Voice "A call comes in" → `https://your-backend-url/twilio/voice` (POST)
5. Set in `.env`:
   ```
   TWILIO_ACCOUNT_SID=your-twilio-account-sid
   TWILIO_AUTH_TOKEN=your-twilio-auth-token
   TWILIO_PHONE_NUMBER=+1234567890
   ```

#### 4. Firebase Auth (Phase 2 — Family Accounts)

Required for user login and family management features.

1. Go to https://console.firebase.google.com
2. Add your GCP project (or create a new one)
3. Enable **Authentication** → Sign-in method → Enable **Google**
4. Go to Project Settings → General → scroll to "Your apps" → Add a **Web app**
5. Copy the Firebase config values
6. Set in `.env`:
   ```
   FIREBASE_PROJECT_ID=your-gcp-project-id
   NEXT_PUBLIC_FIREBASE_API_KEY=your-firebase-api-key
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-gcp-project-id
   ```

#### 5. SendGrid (Email Notifications)

Optional. Used to send family invite emails and new Memory Reel notifications.

1. Create an account at https://sendgrid.com
2. Create an API key with Mail Send permissions
3. Set in `.env`:
   ```
   SENDGRID_API_KEY=your-sendgrid-api-key
   ```

#### 6. FFmpeg (Video Assembly)

Required for Memory Reel video generation.

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### Local Development

#### Quick Start (In-Memory, No GCP Required)

The fastest way to run locally. Uses in-memory storage instead of Firestore — data resets on restart, but no cloud credentials needed.

1. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set at minimum:
   ```
   USE_LOCAL_STORAGE=true
   GEMINI_API_KEY=your-gemini-api-key
   ```

2. **Start the backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

3. **Start the frontend** (in a separate terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

#### Full Setup (With GCP Services)

For production-like local dev with persistent Firestore storage, real phone calls, and media generation.

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Fill in ALL service credentials (see Service Setup above)
   ```
   Make sure `USE_LOCAL_STORAGE` is **not** set (or set to `false`).

2. **Run with Docker Compose:**
   ```bash
   docker-compose up
   ```

3. **Or run individually** (same as Quick Start steps 2-3, without `USE_LOCAL_STORAGE=true`).

### Deployment

```bash
./infra/deploy.sh your-gcp-project-id us-central1
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/elders` | Create elder profile (family setup) |
| GET | `/elders/{id}` | Get elder profile |
| PUT | `/elders/{id}/schedule` | Update call schedule |
| GET | `/elders/{id}/memory` | Get accumulated memory |
| GET | `/elders/{id}/sessions` | List elder's sessions |
| POST | `/elders/{id}/call` | Trigger immediate call |
| GET | `/sessions` | List sessions (filterable) |
| GET | `/sessions/{id}` | Session details |
| GET | `/sessions/{id}/moments` | Story moments |
| GET | `/sessions/{id}/reel` | Memory Reel |
| POST | `/twilio/voice` | Inbound call webhook |
| WS | `/ws/phone-stream` | Phone audio streaming |
| WS | `/ws/pwa-stream` | PWA audio + vision streaming |
| GET | `/health` | Health check |

## How It Works

1. **Family member** visits the app and sets up their elder — name, phone, seed context, schedule.
2. **Nonna calls** the elder at scheduled times (or elder uses the PWA).
3. **Real-time conversation** via Gemini Live API — Nonna remembers everything across sessions.
4. **After each call**, the pipeline runs:
   - Memory extraction (updates elder's persistent context)
   - Story extraction (transcript → structured moments)
   - Image generation (Imagen 3 — warm watercolor illustrations)
   - Narration (Cloud TTS — warm voiceover)
   - Video assembly (FFmpeg — images + audio → MP4)
5. **Family gets notified** and watches Memory Reels in the archive.
