# Nonna Phase 1 — Complete Build Summary

## What Nonna Is

A live conversational AI that calls elders on the phone (or via a camera-enabled PWA), listens to their stories across sessions, and transforms each conversation into a **Memory Reel** — a short narrated video with AI-generated illustrations that families keep forever.

---

## Backend (Python/FastAPI) — 15 service files

### Conversation Engine (`services/conversation.py`)
- Gemini Live API integration with real-time bidirectional audio streaming
- Session lifecycle management (start → accumulate transcript → end → trigger pipeline)

### Nonna's Personality (`prompts/nonna.py`)
- Dynamic system prompt with first-conversation vs. returning-conversation variants
- Phone channel addendum (audio-only cues) vs. PWA addendum (vision instructions)
- Injects elder memory context — people, places, events, themes, story gaps, conversation style

### Twilio Phone Channel (`services/twilio_service.py`, `routers/twilio_voice.py`)
- Inbound call handling: caller ID lookup → session creation → TwiML media stream connection
- Outbound call placement for scheduled calls
- Unknown caller rejection with friendly message

### WebSocket Bridges (`routers/websocket_phone.py`, `routers/websocket_pwa.py`)
- Phone: Twilio Media Streams → mulaw↔PCM conversion → Gemini
- PWA: Browser audio + camera frames (1 per 10s) → Gemini multimodal

### Elder Memory System (`services/memory_extraction.py`)
- Post-session Gemini extraction: people, places, life events, themes, recipes/skills, story gaps
- Merges new info with existing memory (deduplicates, updates)

### Memory Reel Pipeline (`services/reel_pipeline.py`)
- Story extraction: transcript + memory → structured moments (title, summary, quote, visual description)
- Image generation: Imagen 3 via Vertex AI — warm watercolor illustrations
- Narration: Google Cloud TTS — warm voiceover per moment
- Assembly: FFmpeg with Ken Burns effect → MP4 reel
- Async via Cloud Tasks

### Data Layer (`services/firestore.py`, `services/local_storage.py`)
- Full CRUD for elders, sessions, moments, reels, elder memory
- In-memory drop-in replacement for local dev/testing (`USE_LOCAL_STORAGE=true`)

### REST API — 13 endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| POST | `/elders` | Create elder (family setup) |
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
| POST | `/twilio/status` | Call status callback |

### WebSocket Endpoints

| Protocol | Path | Purpose |
|----------|------|---------|
| WS | `/ws/phone-stream` | Phone audio streaming |
| WS | `/ws/pwa-stream` | PWA audio+vision streaming |

### Supporting Services
- `services/scheduling.py` — Cloud Scheduler integration for automated outbound calls
- `services/notifications.py` — Family SMS notifications via Twilio (reel ready, missed calls)
- `services/storage.py` — Cloud Storage uploads (images, audio, transcripts, reels)

---

## Frontend (Next.js/React/Tailwind) — 5 pages + hooks

| Route | Purpose |
|-------|---------|
| `/` | Landing page — explains Nonna, "Set Up Nonna for Your Family" CTA |
| `/setup` | 4-step family setup flow: name → phone → seed context → schedule |
| `/talk/[elderId]` | Elder PWA view — single large "Talk to Nonna" button, camera+mic streaming |
| `/archive/[elderId]` | Family archive — session cards, reel video player, moment browser |

- `useConversation.ts` hook — WebSocket client with audio capture, PCM encoding, camera frame streaming, auto-reconnect
- `lib/api.ts` — Typed API client for all backend endpoints
- PWA manifest for home screen installation
- Elder-friendly design: 18px+ fonts, high contrast, 44px+ touch targets, WCAG accessible

---

## Infrastructure

- **Dockerfiles** — Backend (Python + FFmpeg), Frontend (Next.js standalone)
- **docker-compose.yml** — Local development with both services
- **`infra/deploy.sh`** — Full GCP deployment script (Cloud Run, Firestore, Storage buckets, Cloud Tasks queue, Cloud Scheduler)
- **`.env.example`** — All 20+ environment variables documented

---

## Test Suite — 68/68 passing

| File | Tests | What it covers |
|------|-------|----------------|
| `test_integration.py` | 22 | Full HTTP request/response cycles — elder CRUD, memory, sessions, Twilio webhooks, end-to-end family setup flow, multi-elder independence |
| `test_models.py` | 20 | All Pydantic data models |
| `test_api.py` | 11 | REST endpoints with mocked Firestore |
| `test_prompts.py` | 11 | System prompt generation across all variants |
| `test_twilio.py` | 3 | TwiML generation and protocol conversion |
| `test_config.py` | 2 | Settings defaults and overrides |

---

## Project Structure

```
nonna/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Environment configuration
│   │   ├── models/
│   │   │   ├── elder.py         # Elder, Memory, Schedule models
│   │   │   └── session.py       # Session, Moment, Reel models
│   │   ├── routers/
│   │   │   ├── elders.py        # Elder CRUD + call trigger
│   │   │   ├── sessions.py      # Session + Reel retrieval
│   │   │   ├── twilio_voice.py  # Twilio webhooks
│   │   │   ├── websocket_phone.py  # Phone audio streaming
│   │   │   └── websocket_pwa.py    # PWA audio + vision streaming
│   │   ├── services/
│   │   │   ├── conversation.py  # Gemini Live API engine
│   │   │   ├── firestore.py     # Firestore data access layer
│   │   │   ├── local_storage.py # In-memory storage (dev/test)
│   │   │   ├── memory_extraction.py  # Post-session memory update
│   │   │   ├── reel_pipeline.py # Full reel generation pipeline
│   │   │   ├── scheduling.py    # Outbound call scheduling
│   │   │   ├── notifications.py # Family SMS notifications
│   │   │   ├── storage.py       # Cloud Storage operations
│   │   │   └── twilio_service.py # Twilio voice integration
│   │   └── prompts/
│   │       └── nonna.py         # System prompt + personality
│   ├── tests/
│   │   ├── conftest.py          # Test configuration
│   │   ├── test_api.py          # API endpoint unit tests
│   │   ├── test_config.py       # Settings tests
│   │   ├── test_integration.py  # Full integration tests
│   │   ├── test_models.py       # Pydantic model tests
│   │   ├── test_prompts.py      # System prompt tests
│   │   └── test_twilio.py       # TwiML generation tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Landing page
│   │   │   ├── layout.tsx       # Root layout
│   │   │   ├── globals.css      # Tailwind + custom styles
│   │   │   ├── setup/page.tsx   # Family setup flow
│   │   │   ├── talk/[elderId]/page.tsx    # Elder conversation view
│   │   │   └── archive/[elderId]/page.tsx # Family archive view
│   │   ├── hooks/
│   │   │   └── useConversation.ts # WebSocket conversation hook
│   │   └── lib/
│   │       └── api.ts           # Backend API client
│   ├── public/
│   │   └── manifest.json        # PWA manifest
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── infra/
│   └── deploy.sh                # GCP deployment script
├── docker-compose.yml           # Local development
├── .env.example                 # Environment variables
├── .gitignore
└── README.md
```

---

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

---

## Git History (4 commits on `claude/nonna-phase-1-build-nbZnD`)

1. **Full Phase 1 implementation** — all backend services, frontend pages, infra
2. **Frontend lockfile + Next.js types**
3. **Unit test suite** — 46 tests covering models, API, prompts, TwiML
4. **Integration tests** — in-memory storage backend + 22 integration tests (68 total)
