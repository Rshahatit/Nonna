"""Thread endpoints — auto-generated cross-session story threads."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from app.middleware.auth import require_any_role
from app.models.user import ThreadResponse
from app.services import firestore_families

router = APIRouter()


@router.get("/{family_id}/elders/{elder_id}/threads", response_model=list[ThreadResponse])
async def list_threads(
    family_id: str,
    elder_id: str,
    type: Optional[str] = Query(None, description="Filter by thread type: person, place, theme"),
    auth: dict = Depends(require_any_role),
):
    """List all threads for an elder."""
    return await firestore_families.list_threads(family_id, elder_id, thread_type=type)


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str):
    """Get a thread's details with all linked moments."""
    thread = await firestore_families.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread
