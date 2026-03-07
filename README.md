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
- Docker & Docker Compose
- Google Cloud account with billing enabled
- Twilio account with a phone number
- Gemini API key

### Local Development

1. **Clone and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and credentials
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up
   ```

3. **Or run individually:**
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000

   # Frontend
   cd frontend
   npm install
   npm run dev
   ```

4. **Access:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

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
