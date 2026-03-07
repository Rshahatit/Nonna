"""In-memory storage backend for local development and testing.

Drop-in replacement for firestore.py that stores everything in dictionaries.
Activated when USE_LOCAL_STORAGE=true is set in the environment.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid

from app.models.elder import ElderCreate, ElderMemory, ElderResponse, CallSchedule
from app.models.session import SessionResponse, MomentResponse, ReelResponse

# In-memory stores
_elders: dict[str, dict] = {}
_elder_memories: dict[str, dict] = {}
_sessions: dict[str, dict] = {}
_moments: dict[str, list[dict]] = {}  # session_id -> [moment_dicts]
_reels: dict[str, dict] = {}


def get_db():
    """Stub for code that imports get_db from firestore.

    In local mode, the actual Firestore client is not available.
    Modules that call get_db() at runtime in local mode will raise.
    """
    raise RuntimeError(
        "get_db() is not available in local storage mode. "
        "Use the async helper functions instead."
    )


def reset():
    """Clear all in-memory data. Useful between tests."""
    _elders.clear()
    _elder_memories.clear()
    _sessions.clear()
    _moments.clear()
    _reels.clear()


# ──────────────────────────── Elders ────────────────────────────

async def create_elder(data: ElderCreate) -> ElderResponse:
    elder_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _elders[elder_id] = {
        "name": data.name,
        "phoneNumber": data.phone_number,
        "seedContext": data.seed_context,
        "callSchedule": data.call_schedule.model_dump(),
        "createdAt": now,
        "createdBy": data.created_by,
    }
    _elder_memories[elder_id] = ElderMemory().model_dump()

    return ElderResponse(
        id=elder_id,
        name=data.name,
        phone_number=data.phone_number,
        seed_context=data.seed_context,
        call_schedule=data.call_schedule,
        created_at=now,
        created_by=data.created_by,
    )


async def get_elder(elder_id: str) -> Optional[ElderResponse]:
    if elder_id not in _elders:
        return None
    d = _elders[elder_id]
    return ElderResponse(
        id=elder_id,
        name=d["name"],
        phone_number=d["phoneNumber"],
        seed_context=d.get("seedContext", ""),
        call_schedule=CallSchedule(**d.get("callSchedule", {})),
        created_at=d["createdAt"],
        created_by=d.get("createdBy", ""),
    )


async def get_elder_by_phone(phone_number: str) -> Optional[ElderResponse]:
    for elder_id, d in _elders.items():
        if d["phoneNumber"] == phone_number:
            return ElderResponse(
                id=elder_id,
                name=d["name"],
                phone_number=d["phoneNumber"],
                seed_context=d.get("seedContext", ""),
                call_schedule=CallSchedule(**d.get("callSchedule", {})),
                created_at=d["createdAt"],
                created_by=d.get("createdBy", ""),
            )
    return None


async def update_elder_schedule(elder_id: str, schedule: CallSchedule) -> bool:
    if elder_id not in _elders:
        return False
    _elders[elder_id]["callSchedule"] = schedule.model_dump()
    return True


# ──────────────────────────── Elder Memory ────────────────────────────

async def get_elder_memory(elder_id: str) -> ElderMemory:
    if elder_id not in _elder_memories:
        return ElderMemory()
    return ElderMemory(**_elder_memories[elder_id])


async def update_elder_memory(elder_id: str, memory: ElderMemory) -> None:
    _elder_memories[elder_id] = memory.model_dump()


# ──────────────────────────── Sessions ────────────────────────────

async def create_session(elder_id: str, channel: str) -> SessionResponse:
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _sessions[session_id] = {
        "elderId": elder_id,
        "channel": channel,
        "status": "live",
        "startedAt": now,
        "endedAt": None,
        "duration": None,
        "transcriptUrl": "",
        "visionContextUsed": channel == "pwa",
        "topicsCovered": [],
        "newPeopleMentioned": [],
    }
    _moments[session_id] = []

    return SessionResponse(
        id=session_id,
        elder_id=elder_id,
        channel=channel,
        status="live",
        started_at=now,
    )


async def get_session(session_id: str) -> Optional[SessionResponse]:
    if session_id not in _sessions:
        return None
    d = _sessions[session_id]
    return SessionResponse(
        id=session_id,
        elder_id=d["elderId"],
        channel=d["channel"],
        status=d["status"],
        started_at=d["startedAt"],
        ended_at=d.get("endedAt"),
        duration=d.get("duration"),
        transcript_url=d.get("transcriptUrl", ""),
        vision_context_used=d.get("visionContextUsed", False),
        topics_covered=d.get("topicsCovered", []),
        new_people_mentioned=d.get("newPeopleMentioned", []),
    )


async def update_session_status(session_id: str, status: str, **kwargs) -> None:
    if session_id in _sessions:
        _sessions[session_id]["status"] = status
        _sessions[session_id].update(kwargs)


async def list_sessions(elder_id: Optional[str] = None, status: Optional[str] = None,
                        channel: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[SessionResponse]:
    results = []
    for sid, d in _sessions.items():
        if elder_id and d["elderId"] != elder_id:
            continue
        if status and d["status"] != status:
            continue
        if channel and d["channel"] != channel:
            continue
        results.append(SessionResponse(
            id=sid,
            elder_id=d["elderId"],
            channel=d["channel"],
            status=d["status"],
            started_at=d["startedAt"],
            ended_at=d.get("endedAt"),
            duration=d.get("duration"),
            transcript_url=d.get("transcriptUrl", ""),
            vision_context_used=d.get("visionContextUsed", False),
            topics_covered=d.get("topicsCovered", []),
            new_people_mentioned=d.get("newPeopleMentioned", []),
        ))
    # Sort by startedAt descending
    results.sort(key=lambda s: s.started_at, reverse=True)
    return results[offset:offset + limit]


# ──────────────────────────── Moments ────────────────────────────

async def create_moment(session_id: str, moment_data: dict) -> MomentResponse:
    moment_id = str(uuid.uuid4())
    moment_data["id"] = moment_id
    if session_id not in _moments:
        _moments[session_id] = []
    _moments[session_id].append(moment_data)
    return MomentResponse(id=moment_id, **{k: v for k, v in moment_data.items() if k != "id"})


async def list_moments(session_id: str) -> list[MomentResponse]:
    if session_id not in _moments:
        return []
    moments = sorted(_moments[session_id], key=lambda m: m.get("order", 0))
    return [MomentResponse(id=m["id"], **{k: v for k, v in m.items() if k != "id"}) for m in moments]


# ──────────────────────────── Reels ────────────────────────────

async def create_reel(session_id: str, elder_id: str) -> ReelResponse:
    reel_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _reels[reel_id] = {
        "sessionId": session_id,
        "elderId": elder_id,
        "status": "generating",
        "videoUrl": "",
        "thumbnailUrl": "",
        "duration": None,
        "createdAt": now,
    }
    return ReelResponse(
        id=reel_id,
        session_id=session_id,
        elder_id=elder_id,
        status="generating",
        created_at=now,
    )


async def get_reel_by_session(session_id: str) -> Optional[ReelResponse]:
    for reel_id, d in _reels.items():
        if d["sessionId"] == session_id:
            return ReelResponse(
                id=reel_id,
                session_id=d["sessionId"],
                elder_id=d["elderId"],
                status=d["status"],
                video_url=d.get("videoUrl", ""),
                thumbnail_url=d.get("thumbnailUrl", ""),
                duration=d.get("duration"),
                created_at=d["createdAt"],
            )
    return None


async def update_reel(reel_id: str, **kwargs) -> None:
    if reel_id in _reels:
        _reels[reel_id].update(kwargs)
