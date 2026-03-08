"""In-memory storage backend that mirrors the firestore.py interface.

Used for local development when USE_LOCAL_STORAGE=true.
Data lives only in process memory and is lost on restart.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid
import copy

from app.models.elder import ElderCreate, ElderMemory, ElderResponse, CallSchedule
from app.models.session import SessionResponse, MomentResponse, ReelResponse

# In-memory stores
_elders: dict[str, dict] = {}
_elder_memory: dict[str, dict] = {}
_sessions: dict[str, dict] = {}
_moments: dict[str, dict[str, dict]] = {}  # session_id -> {moment_id -> data}
_reels: dict[str, dict] = {}


def get_db():
    """Compatibility stub — returns None since we don't use a DB client."""
    return None


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
    _elder_memory[elder_id] = ElderMemory().model_dump()

    return ElderResponse(
        id=elder_id, name=data.name, phone_number=data.phone_number,
        seed_context=data.seed_context, call_schedule=data.call_schedule,
        created_at=now, created_by=data.created_by,
    )


async def get_elder(elder_id: str) -> Optional[ElderResponse]:
    d = _elders.get(elder_id)
    if not d:
        return None
    return ElderResponse(
        id=elder_id, name=d["name"], phone_number=d["phoneNumber"],
        seed_context=d.get("seedContext", ""),
        call_schedule=CallSchedule(**d.get("callSchedule", {})),
        created_at=d["createdAt"], created_by=d.get("createdBy", ""),
    )


async def get_elder_by_phone(phone_number: str) -> Optional[ElderResponse]:
    for eid, d in _elders.items():
        if d["phoneNumber"] == phone_number:
            return ElderResponse(
                id=eid, name=d["name"], phone_number=d["phoneNumber"],
                seed_context=d.get("seedContext", ""),
                call_schedule=CallSchedule(**d.get("callSchedule", {})),
                created_at=d["createdAt"], created_by=d.get("createdBy", ""),
            )
    return None


async def update_elder_schedule(elder_id: str, schedule: CallSchedule) -> bool:
    if elder_id not in _elders:
        return False
    _elders[elder_id]["callSchedule"] = schedule.model_dump()
    return True


# ──────────────────────────── Elder Memory ────────────────────────────

async def get_elder_memory(elder_id: str) -> ElderMemory:
    d = _elder_memory.get(elder_id)
    if not d:
        return ElderMemory()
    return ElderMemory(**d)


async def update_elder_memory(elder_id: str, memory: ElderMemory) -> None:
    _elder_memory[elder_id] = memory.model_dump()


# ──────────────────────────── Sessions ────────────────────────────

async def create_session(elder_id: str, channel: str, mode: str = "story") -> SessionResponse:
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _sessions[session_id] = {
        "elderId": elder_id,
        "channel": channel,
        "mode": mode,
        "status": "live",
        "startedAt": now,
        "endedAt": None,
        "duration": None,
        "transcriptUrl": "",
        "visionContextUsed": channel == "pwa",
        "topicsCovered": [],
        "newPeopleMentioned": [],
        "modeTransitions": [],
        "navigationContext": None,
    }
    _moments[session_id] = {}

    return SessionResponse(
        id=session_id, elder_id=elder_id, channel=channel,
        mode=mode, status="live", started_at=now,
    )


async def get_session(session_id: str) -> Optional[SessionResponse]:
    d = _sessions.get(session_id)
    if not d:
        return None
    return SessionResponse(
        id=session_id, elder_id=d["elderId"], channel=d["channel"],
        mode=d.get("mode", "story"),
        status=d["status"], started_at=d["startedAt"],
        ended_at=d.get("endedAt"), duration=d.get("duration"),
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
            id=sid, elder_id=d["elderId"], channel=d["channel"],
            status=d["status"], started_at=d["startedAt"],
            ended_at=d.get("endedAt"), duration=d.get("duration"),
            transcript_url=d.get("transcriptUrl", ""),
            vision_context_used=d.get("visionContextUsed", False),
            topics_covered=d.get("topicsCovered", []),
            new_people_mentioned=d.get("newPeopleMentioned", []),
        ))
    results.sort(key=lambda s: s.started_at, reverse=True)
    return results[offset:offset + limit]


# ──────────────────────────── Moments ────────────────────────────

async def create_moment(session_id: str, moment_data: dict) -> MomentResponse:
    moment_id = str(uuid.uuid4())
    moment_data = copy.deepcopy(moment_data)
    moment_data["id"] = moment_id
    if session_id not in _moments:
        _moments[session_id] = {}
    _moments[session_id][moment_id] = moment_data
    return MomentResponse(id=moment_id, **{k: v for k, v in moment_data.items() if k != "id"})


async def list_moments(session_id: str) -> list[MomentResponse]:
    moments = _moments.get(session_id, {})
    results = []
    for mid, d in moments.items():
        results.append(MomentResponse(id=mid, **{k: v for k, v in d.items() if k != "id"}))
    results.sort(key=lambda m: m.order if hasattr(m, 'order') and m.order is not None else 0)
    return results


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
        id=reel_id, session_id=session_id, elder_id=elder_id,
        status="generating", created_at=now,
    )


async def get_reel_by_session(session_id: str) -> Optional[ReelResponse]:
    for rid, d in _reels.items():
        if d["sessionId"] == session_id:
            return ReelResponse(
                id=rid, session_id=d["sessionId"], elder_id=d["elderId"],
                status=d["status"], video_url=d.get("videoUrl", ""),
                thumbnail_url=d.get("thumbnailUrl", ""),
                duration=d.get("duration"), created_at=d["createdAt"],
            )
    return None


async def update_reel(reel_id: str, **kwargs) -> None:
    if reel_id in _reels:
        _reels[reel_id].update(kwargs)
