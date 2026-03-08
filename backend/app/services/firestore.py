"""Firestore data access layer for all collections."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from google.cloud import firestore
from app.config import get_settings
from app.models.elder import ElderCreate, ElderMemory, ElderResponse, CallSchedule
from app.models.session import SessionResponse, MomentResponse, ReelResponse

_db: Optional[firestore.AsyncClient] = None


def get_db() -> firestore.AsyncClient:
    global _db
    if _db is None:
        settings = get_settings()
        _db = firestore.AsyncClient(
            project=settings.google_cloud_project,
            database=settings.firestore_database,
        )
    return _db


# ──────────────────────────── Elders ────────────────────────────

async def create_elder(data: ElderCreate) -> ElderResponse:
    db = get_db()
    elder_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "name": data.name,
        "phoneNumber": data.phone_number,
        "seedContext": data.seed_context,
        "callSchedule": data.call_schedule.model_dump(),
        "createdAt": now,
        "createdBy": data.created_by,
    }
    await db.collection("elders").document(elder_id).set(doc)

    # Initialize empty memory
    await db.collection("elders").document(elder_id).collection("memory").document("current").set(
        ElderMemory().model_dump()
    )

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
    db = get_db()
    doc = await db.collection("elders").document(elder_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    return ElderResponse(
        id=doc.id,
        name=d["name"],
        phone_number=d["phoneNumber"],
        seed_context=d.get("seedContext", ""),
        call_schedule=CallSchedule(**d.get("callSchedule", {})),
        created_at=d["createdAt"],
        created_by=d.get("createdBy", ""),
    )


async def get_elder_by_phone(phone_number: str) -> Optional[ElderResponse]:
    db = get_db()
    query = db.collection("elders").where("phoneNumber", "==", phone_number).limit(1)
    docs = []
    async for doc in query.stream():
        docs.append(doc)
    if not docs:
        return None
    d = docs[0].to_dict()
    return ElderResponse(
        id=docs[0].id,
        name=d["name"],
        phone_number=d["phoneNumber"],
        seed_context=d.get("seedContext", ""),
        call_schedule=CallSchedule(**d.get("callSchedule", {})),
        created_at=d["createdAt"],
        created_by=d.get("createdBy", ""),
    )


async def update_elder_schedule(elder_id: str, schedule: CallSchedule) -> bool:
    db = get_db()
    doc_ref = db.collection("elders").document(elder_id)
    doc = await doc_ref.get()
    if not doc.exists:
        return False
    await doc_ref.update({"callSchedule": schedule.model_dump()})
    return True


# ──────────────────────────── Elder Memory ────────────────────────────

async def get_elder_memory(elder_id: str) -> ElderMemory:
    db = get_db()
    doc = await db.collection("elders").document(elder_id).collection("memory").document("current").get()
    if not doc.exists:
        return ElderMemory()
    return ElderMemory(**doc.to_dict())


async def update_elder_memory(elder_id: str, memory: ElderMemory) -> None:
    db = get_db()
    await db.collection("elders").document(elder_id).collection("memory").document("current").set(
        memory.model_dump()
    )


# ──────────────────────────── Sessions ────────────────────────────

async def create_session(elder_id: str, channel: str, mode: str = "story") -> SessionResponse:
    db = get_db()
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
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
    await db.collection("sessions").document(session_id).set(doc)

    return SessionResponse(
        id=session_id,
        elder_id=elder_id,
        channel=channel,
        mode=mode,
        status="live",
        started_at=now,
    )


async def get_session(session_id: str) -> Optional[SessionResponse]:
    db = get_db()
    doc = await db.collection("sessions").document(session_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    return SessionResponse(
        id=doc.id,
        elder_id=d["elderId"],
        channel=d["channel"],
        mode=d.get("mode", "story"),
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
    db = get_db()
    update = {"status": status, **kwargs}
    await db.collection("sessions").document(session_id).update(update)


async def list_sessions(elder_id: Optional[str] = None, status: Optional[str] = None,
                        channel: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[SessionResponse]:
    db = get_db()
    query = db.collection("sessions")
    if elder_id:
        query = query.where("elderId", "==", elder_id)
    if status:
        query = query.where("status", "==", status)
    if channel:
        query = query.where("channel", "==", channel)
    query = query.order_by("startedAt", direction=firestore.Query.DESCENDING).limit(limit).offset(offset)

    results = []
    async for doc in query.stream():
        d = doc.to_dict()
        results.append(SessionResponse(
            id=doc.id,
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
    return results


# ──────────────────────────── Moments ────────────────────────────

async def create_moment(session_id: str, moment_data: dict) -> MomentResponse:
    db = get_db()
    moment_id = str(uuid.uuid4())
    moment_data["id"] = moment_id
    await db.collection("sessions").document(session_id).collection("moments").document(moment_id).set(moment_data)
    return MomentResponse(id=moment_id, **{k: v for k, v in moment_data.items() if k != "id"})


async def list_moments(session_id: str) -> list[MomentResponse]:
    db = get_db()
    query = db.collection("sessions").document(session_id).collection("moments").order_by("order")
    results = []
    async for doc in query.stream():
        d = doc.to_dict()
        results.append(MomentResponse(id=doc.id, **{k: v for k, v in d.items() if k != "id"}))
    return results


# ──────────────────────────── Reels ────────────────────────────

async def create_reel(session_id: str, elder_id: str) -> ReelResponse:
    db = get_db()
    reel_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "sessionId": session_id,
        "elderId": elder_id,
        "status": "generating",
        "videoUrl": "",
        "thumbnailUrl": "",
        "duration": None,
        "createdAt": now,
    }
    await db.collection("reels").document(reel_id).set(doc)
    return ReelResponse(
        id=reel_id,
        session_id=session_id,
        elder_id=elder_id,
        status="generating",
        created_at=now,
    )


async def get_reel_by_session(session_id: str) -> Optional[ReelResponse]:
    db = get_db()
    query = db.collection("reels").where("sessionId", "==", session_id).limit(1)
    docs = []
    async for doc in query.stream():
        docs.append(doc)
    if not docs:
        return None
    d = docs[0].to_dict()
    return ReelResponse(
        id=docs[0].id,
        session_id=d["sessionId"],
        elder_id=d["elderId"],
        status=d["status"],
        video_url=d.get("videoUrl", ""),
        thumbnail_url=d.get("thumbnailUrl", ""),
        duration=d.get("duration"),
        created_at=d["createdAt"],
    )


async def update_reel(reel_id: str, **kwargs) -> None:
    db = get_db()
    await db.collection("reels").document(reel_id).update(kwargs)
