"""Nonna Backend — FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    elders, sessions, twilio_voice, websocket_phone, websocket_pwa,
    auth, families, invites, collections, threads, search, books,
)
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Nonna API",
    description="Live conversational AI that helps elders preserve their stories.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.next_public_app_url,
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 1 routers
app.include_router(elders.router, prefix="/elders", tags=["elders"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(twilio_voice.router, prefix="/twilio", tags=["twilio"])
app.include_router(websocket_phone.router, tags=["websocket"])
app.include_router(websocket_pwa.router, tags=["websocket"])

# Phase 2 routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(families.router, prefix="/families", tags=["families"])
app.include_router(invites.router, prefix="/invites", tags=["invites"])
app.include_router(collections.router, prefix="/families", tags=["collections"])
app.include_router(threads.router, prefix="/families", tags=["threads"])
app.include_router(search.router, prefix="/families", tags=["search"])
app.include_router(books.router, prefix="/families", tags=["books"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nonna-api", "version": "0.2.0"}
