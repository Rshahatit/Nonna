"""Session and Reel API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.session import SessionResponse, MomentResponse, ReelResponse
from app.services import firestore

router = APIRouter()


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    elder_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List sessions with optional filtering."""
    return await firestore.list_sessions(
        elder_id=elder_id,
        status=status,
        channel=channel,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details."""
    session = await firestore.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/moments", response_model=list[MomentResponse])
async def get_moments(session_id: str):
    """List all moments for a session."""
    session = await firestore.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await firestore.list_moments(session_id)


@router.get("/{session_id}/reel", response_model=ReelResponse)
async def get_reel(session_id: str):
    """Get the Memory Reel for a session."""
    reel = await firestore.get_reel_by_session(session_id)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found for this session")
    return reel
