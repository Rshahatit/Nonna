"""Elder management API endpoints."""

from fastapi import APIRouter, HTTPException

from app.models.elder import ElderCreate, ElderResponse, ElderScheduleUpdate, ElderMemory
from app.models.session import SessionResponse
from app.services import firestore
from app.services.twilio_service import place_outbound_call

router = APIRouter()


@router.post("", response_model=ElderResponse, status_code=201)
async def create_elder(data: ElderCreate):
    """Create a new elder profile (used by family setup flow)."""
    return await firestore.create_elder(data)


@router.get("/{elder_id}", response_model=ElderResponse)
async def get_elder(elder_id: str):
    """Retrieve an elder's profile."""
    elder = await firestore.get_elder(elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")
    return elder


@router.put("/{elder_id}/schedule", response_model=dict)
async def update_schedule(elder_id: str, data: ElderScheduleUpdate):
    """Update an elder's call schedule."""
    success = await firestore.update_elder_schedule(elder_id, data.call_schedule)
    if not success:
        raise HTTPException(status_code=404, detail="Elder not found")
    return {"status": "updated"}


@router.get("/{elder_id}/memory", response_model=ElderMemory)
async def get_memory(elder_id: str):
    """Retrieve an elder's accumulated memory context."""
    elder = await firestore.get_elder(elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")
    return await firestore.get_elder_memory(elder_id)


@router.get("/{elder_id}/sessions", response_model=list[SessionResponse])
async def list_elder_sessions(elder_id: str, limit: int = 50, offset: int = 0):
    """List all sessions for an elder."""
    elder = await firestore.get_elder(elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")
    return await firestore.list_sessions(elder_id=elder_id, limit=limit, offset=offset)


@router.post("/{elder_id}/call", response_model=dict)
async def trigger_call(elder_id: str):
    """Trigger an immediate outbound call to an elder."""
    elder = await firestore.get_elder(elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")

    call_sid = await place_outbound_call(elder_id)
    if not call_sid:
        raise HTTPException(status_code=500, detail="Failed to place call")
    return {"status": "calling", "call_sid": call_sid}
