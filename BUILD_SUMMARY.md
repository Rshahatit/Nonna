# Nonna — Complete Build Summary

## What Nonna Is

A live conversational AI that calls elders on the phone (or via a camera-enabled PWA), listens to their stories across sessions, and transforms each conversation into a **Memory Reel** — a short narrated video with AI-generated illustrations that families keep forever.

---

## Phase 1 — Core Conversation & Memory Reels

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

---

## Phase 2 — Family Organization & Richer Archive

### User Authentication (`routers/auth.py`, `middleware/auth.py`)
- Firebase Auth integration with Google sign-in
- JWT token verification middleware
- Dev auth bypass for local testing without Firebase

### Family Management (`routers/families.py`, `services/firestore_families.py`)
- Family groups that own one or more elders
- Role-based membership: organizer, member, viewer
- Per-member notification preferences

### Invite System (`routers/invites.py`)
- Token-based family invites with configurable expiration
- Email-based invite flow (via SendGrid)
- Invite redemption, listing, and revocation

### Collections (`routers/collections.py`)
- User-curated groupings of moments across sessions
- Add/remove moments, public/private visibility
- Family-scoped collection browsing

### Threads (`routers/threads.py`)
- Auto-generated thematic threads (topics, people, places)
- Cross-session moment aggregation

### Smart Tagging (`services/tagging.py`)
- Automated moment tagging with topics, people, places
- Searchable metadata across the archive

### Search (`routers/search.py`)
- Full-text search across moments
- Filterable by tags, people, date range, channel

### Books (`routers/books.py`, `services/book_generator.py`)
- PDF memory book generation from sessions or collections
- WeasyPrint-based PDF rendering

### Notifications v2 (`services/notifications_v2.py`)
- SendGrid email notifications for new reels, invites, weekly digests

---

## REST API Endpoints

### Phase 1 — Core

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

### Phase 2 — Families & Archive

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/login` | Firebase token → session |
| GET | `/auth/me` | Current user profile |
| POST | `/families` | Create family group |
| GET | `/families/{id}` | Get family details |
| PUT | `/families/{id}` | Update family |
| GET | `/families/{id}/members` | List members |
| PUT | `/families/{id}/members/{uid}` | Update member role/prefs |
| DELETE | `/families/{id}/members/{uid}` | Remove member |
| POST | `/families/{id}/elders/{eid}` | Add elder to family |
| POST | `/families/{id}/invites` | Create invite |
| GET | `/families/{id}/invites` | List invites |
| DELETE | `/invites/{id}` | Revoke invite |
| POST | `/invites/redeem` | Redeem invite token |
| POST | `/families/{id}/collections` | Create collection |
| GET | `/families/{id}/collections` | List collections |
| PUT | `/collections/{id}` | Update collection |
| DELETE | `/collections/{id}` | Delete collection |
| POST | `/collections/{id}/moments` | Add moment to collection |
| DELETE | `/collections/{id}/moments` | Remove moment |
| GET | `/families/{id}/threads` | List threads |
| GET | `/threads/{id}` | Get thread details |
| POST | `/families/{id}/books` | Generate memory book |
| GET | `/families/{id}/books` | List books |
| GET | `/books/{id}` | Get book details |
| GET | `/search/moments` | Search moments |

### WebSocket Endpoints

| Protocol | Path | Purpose |
|----------|------|---------|
| WS | `/ws/phone-stream` | Phone audio streaming |
| WS | `/ws/pwa-stream` | PWA audio+vision streaming |

---

## Frontend Pages

| Route | Purpose |
|-------|---------|
| `/` | Landing page — explains Nonna, CTA to get started |
| `/setup` | 4-step family setup flow: name → phone → seed context → schedule |
| `/talk/[elderId]` | Elder PWA view — "Talk to Nonna" button, camera+mic streaming |
| `/archive/[elderId]` | Family archive — session cards, reel player, moment browser |
| `/dashboard` | Family dashboard — elder overview, recent sessions |
| `/family` | Family management — members, invites, settings |
| `/invite` | Invite redemption page |

---

## Local Development

Two storage modes:

- **`USE_LOCAL_STORAGE=true`** — In-memory dicts, no GCP needed. Data resets on restart. Great for UI/UX iteration.
- **`USE_LOCAL_STORAGE=false`** (default) — Real Firestore. Requires GCP credentials.

The `app/services/__init__.py` swap mechanism registers `local_storage` / `local_storage_families` under the real module names at import time, so all `from app.services.firestore import ...` calls resolve transparently.

---

## Test Suite — 68 tests

| File | Tests | Coverage |
|------|-------|----------|
| `test_integration.py` | 22 | Full HTTP request/response cycles — elder CRUD, memory, sessions, Twilio webhooks, end-to-end flow |
| `test_models.py` | 20 | All Pydantic data models |
| `test_api.py` | 11 | REST endpoints with mocked Firestore |
| `test_prompts.py` | 11 | System prompt generation across all variants |
| `test_twilio.py` | 3 | TwiML generation and protocol conversion |
| `test_config.py` | 2 | Settings defaults and overrides |

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
| Auth | Firebase Authentication |
| Email | SendGrid |
| PDF Generation | WeasyPrint |
| Hosting | Google Cloud Run |
| Task Queue | Google Cloud Tasks |
| Scheduling | Google Cloud Scheduler |

---

## Git History

1. **Phase 1 implementation** — all backend services, frontend pages, infra
2. **Frontend lockfile + Next.js types**
3. **Unit test suite** — 46 tests covering models, API, prompts, TwiML
4. **Integration tests** — in-memory storage backend + 22 integration tests
5. **Build summary document**
6. **Phase 2: Family Organization** — auth, families, invites, collections, threads, books, search, tagging, notifications v2
7. **Local dev support** — in-memory Phase 2 storage, dev auth bypass, Firebase graceful degradation
8. **Docker build fixes** — ensure public dir exists, default build env vars
