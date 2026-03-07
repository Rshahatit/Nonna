"""In-memory storage backend for Phase 2 family features.

Drop-in replacement for firestore_families.py for local development/testing.
Activated when USE_LOCAL_STORAGE=true is set in the environment.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import secrets

from app.models.user import (
    UserResponse, FamilyResponse, FamilyMemberResponse, FamilyMemberUpdate,
    NotificationPrefs, InviteCreate, InviteResponse,
    CollectionCreate, CollectionResponse, CollectionUpdate, MomentRef,
    ThreadResponse, BookCreate, BookResponse,
)

# In-memory stores
_users: dict[str, dict] = {}
_families: dict[str, dict] = {}
_family_members: dict[str, dict[str, dict]] = {}  # family_id -> {user_id -> member_data}
_invites: dict[str, dict] = {}
_collections: dict[str, dict] = {}
_threads: dict[str, dict] = {}
_books: dict[str, dict] = {}


def reset():
    """Clear all in-memory data."""
    _users.clear()
    _families.clear()
    _family_members.clear()
    _invites.clear()
    _collections.clear()
    _threads.clear()
    _books.clear()


# ──────────────────────────── Users ────────────────────────────

async def upsert_user(uid: str, email: str, name: str, photo_url: str = "",
                      provider: str = "google") -> UserResponse:
    now = datetime.now(timezone.utc)
    if uid in _users:
        _users[uid]["name"] = name
        _users[uid]["photoUrl"] = photo_url
        _users[uid]["lastLoginAt"] = now
    else:
        _users[uid] = {
            "email": email,
            "name": name,
            "photoUrl": photo_url,
            "provider": provider,
            "createdAt": now,
            "lastLoginAt": now,
        }
    d = _users[uid]
    return UserResponse(
        id=uid, email=d["email"], name=d["name"],
        photo_url=d.get("photoUrl", ""), provider=d.get("provider", provider),
        created_at=d["createdAt"],
    )


async def get_user(uid: str) -> Optional[UserResponse]:
    if uid not in _users:
        return None
    d = _users[uid]
    return UserResponse(
        id=uid, email=d["email"], name=d["name"],
        photo_url=d.get("photoUrl", ""), provider=d.get("provider", "google"),
        created_at=d["createdAt"],
    )


async def get_user_by_email(email: str) -> Optional[UserResponse]:
    for uid, d in _users.items():
        if d["email"] == email:
            return UserResponse(
                id=uid, email=d["email"], name=d["name"],
                photo_url=d.get("photoUrl", ""), provider=d.get("provider", "google"),
                created_at=d["createdAt"],
            )
    return None


# ──────────────────────────── Families ────────────────────────────

async def create_family(name: str, created_by: str, elder_ids: list[str] = None) -> FamilyResponse:
    family_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _families[family_id] = {
        "name": name,
        "createdBy": created_by,
        "createdAt": now,
        "elderIds": elder_ids or [],
    }

    # Add creator as organizer
    if family_id not in _family_members:
        _family_members[family_id] = {}
    _family_members[family_id][created_by] = {
        "role": "organizer",
        "joinedAt": now,
        "notificationPrefs": NotificationPrefs().model_dump(),
    }

    return FamilyResponse(
        id=family_id, name=name, created_by=created_by,
        created_at=now, elder_ids=elder_ids or [],
    )


async def get_family(family_id: str) -> Optional[FamilyResponse]:
    if family_id not in _families:
        return None
    d = _families[family_id]
    return FamilyResponse(
        id=family_id, name=d["name"], created_by=d["createdBy"],
        created_at=d["createdAt"], elder_ids=d.get("elderIds", []),
    )


async def update_family(family_id: str, name: str) -> bool:
    if family_id not in _families:
        return False
    _families[family_id]["name"] = name
    return True


async def add_elder_to_family(family_id: str, elder_id: str) -> bool:
    if family_id not in _families:
        return False
    if elder_id not in _families[family_id].get("elderIds", []):
        _families[family_id].setdefault("elderIds", []).append(elder_id)
    return True


async def list_user_families(user_id: str) -> list[FamilyResponse]:
    results = []
    for family_id, members in _family_members.items():
        if user_id in members:
            family = await get_family(family_id)
            if family:
                results.append(family)
    return results


# ──────────────────────────── Family Members ────────────────────────────

async def get_family_member(family_id: str, user_id: str) -> Optional[FamilyMemberResponse]:
    members = _family_members.get(family_id, {})
    if user_id not in members:
        return None
    d = members[user_id]
    user = await get_user(user_id)
    return FamilyMemberResponse(
        user_id=user_id,
        role=d["role"],
        joined_at=d["joinedAt"],
        notification_prefs=NotificationPrefs(**d.get("notificationPrefs", {})),
        name=user.name if user else "",
        email=user.email if user else "",
        photo_url=user.photo_url if user else "",
    )


async def list_family_members(family_id: str) -> list[FamilyMemberResponse]:
    members = _family_members.get(family_id, {})
    results = []
    for user_id, d in members.items():
        user = await get_user(user_id)
        results.append(FamilyMemberResponse(
            user_id=user_id,
            role=d["role"],
            joined_at=d["joinedAt"],
            notification_prefs=NotificationPrefs(**d.get("notificationPrefs", {})),
            name=user.name if user else "",
            email=user.email if user else "",
            photo_url=user.photo_url if user else "",
        ))
    return results


async def update_family_member(family_id: str, user_id: str,
                                update: FamilyMemberUpdate) -> bool:
    members = _family_members.get(family_id, {})
    if user_id not in members:
        return False
    if update.role is not None:
        members[user_id]["role"] = update.role
    if update.notification_prefs is not None:
        members[user_id]["notificationPrefs"] = update.notification_prefs.model_dump()
    return True


async def remove_family_member(family_id: str, user_id: str) -> bool:
    members = _family_members.get(family_id, {})
    if user_id not in members:
        return False
    del members[user_id]
    return True


async def add_family_member(family_id: str, user_id: str, role: str = "member") -> FamilyMemberResponse:
    now = datetime.now(timezone.utc)
    prefs = NotificationPrefs()
    if family_id not in _family_members:
        _family_members[family_id] = {}
    _family_members[family_id][user_id] = {
        "role": role,
        "joinedAt": now,
        "notificationPrefs": prefs.model_dump(),
    }
    user = await get_user(user_id)
    return FamilyMemberResponse(
        user_id=user_id, role=role, joined_at=now,
        notification_prefs=prefs,
        name=user.name if user else "",
        email=user.email if user else "",
        photo_url=user.photo_url if user else "",
    )


# ──────────────────────────── Invites ────────────────────────────

async def create_invite(family_id: str, created_by: str,
                        data: InviteCreate) -> InviteResponse:
    invite_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    family = await get_family(family_id)
    creator = await get_user(created_by)

    _invites[invite_id] = {
        "familyId": family_id,
        "email": data.email,
        "role": data.role,
        "token": token,
        "createdBy": created_by,
        "createdAt": now,
        "expiresAt": now + timedelta(days=data.expires_in_days),
        "redeemedAt": None,
        "status": "pending",
    }

    return InviteResponse(
        id=invite_id, family_id=family_id, email=data.email,
        role=data.role, token=token, created_by=created_by,
        created_at=now, status="pending",
        family_name=family.name if family else "",
        inviter_name=creator.name if creator else "",
    )


async def get_invite_by_token(token: str) -> Optional[InviteResponse]:
    for invite_id, d in _invites.items():
        if d["token"] == token:
            now = datetime.now(timezone.utc)
            status = d["status"]
            if status == "pending" and d.get("expiresAt") and d["expiresAt"] < now:
                status = "expired"
                d["status"] = "expired"

            family = await get_family(d["familyId"])
            creator = await get_user(d["createdBy"])

            return InviteResponse(
                id=invite_id, family_id=d["familyId"], email=d.get("email"),
                role=d["role"], token=d["token"], created_by=d["createdBy"],
                created_at=d["createdAt"], redeemed_at=d.get("redeemedAt"),
                status=status,
                family_name=family.name if family else "",
                inviter_name=creator.name if creator else "",
            )
    return None


async def redeem_invite(token: str, user_id: str) -> Optional[FamilyMemberResponse]:
    invite = await get_invite_by_token(token)
    if not invite or invite.status != "pending":
        return None

    existing = await get_family_member(invite.family_id, user_id)
    if existing:
        return existing

    member = await add_family_member(invite.family_id, user_id, invite.role)

    now = datetime.now(timezone.utc)
    for inv_id, d in _invites.items():
        if d["token"] == token:
            d["status"] = "redeemed"
            d["redeemedAt"] = now
            break

    return member


async def list_family_invites(family_id: str) -> list[InviteResponse]:
    results = []
    for invite_id, d in _invites.items():
        if d["familyId"] == family_id:
            family = await get_family(d["familyId"])
            creator = await get_user(d["createdBy"])
            results.append(InviteResponse(
                id=invite_id, family_id=d["familyId"], email=d.get("email"),
                role=d["role"], token=d["token"], created_by=d["createdBy"],
                created_at=d["createdAt"], redeemed_at=d.get("redeemedAt"),
                status=d["status"],
                family_name=family.name if family else "",
                inviter_name=creator.name if creator else "",
            ))
    results.sort(key=lambda i: i.created_at, reverse=True)
    return results


async def revoke_invite(invite_id: str) -> bool:
    if invite_id not in _invites:
        return False
    if _invites[invite_id]["status"] != "pending":
        return False
    _invites[invite_id]["status"] = "expired"
    return True


# ──────────────────────────── Collections ────────────────────────────

async def create_collection(family_id: str, created_by: str,
                            data: CollectionCreate) -> CollectionResponse:
    collection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _collections[collection_id] = {
        "familyId": family_id,
        "elderId": data.elder_id,
        "name": data.name,
        "description": data.description,
        "coverImageUrl": "",
        "createdBy": created_by,
        "createdAt": now,
        "momentRefs": [],
        "isPublic": False,
    }

    return CollectionResponse(
        id=collection_id, family_id=family_id, elder_id=data.elder_id,
        name=data.name, description=data.description,
        created_by=created_by, created_at=now,
    )


async def get_collection(collection_id: str) -> Optional[CollectionResponse]:
    if collection_id not in _collections:
        return None
    d = _collections[collection_id]
    return CollectionResponse(
        id=collection_id, family_id=d["familyId"], elder_id=d.get("elderId", ""),
        name=d["name"], description=d.get("description", ""),
        cover_image_url=d.get("coverImageUrl", ""),
        created_by=d["createdBy"], created_at=d["createdAt"],
        moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
        is_public=d.get("isPublic", False),
    )


async def list_collections(family_id: str) -> list[CollectionResponse]:
    results = []
    for cid, d in _collections.items():
        if d["familyId"] == family_id:
            results.append(CollectionResponse(
                id=cid, family_id=d["familyId"], elder_id=d.get("elderId", ""),
                name=d["name"], description=d.get("description", ""),
                cover_image_url=d.get("coverImageUrl", ""),
                created_by=d["createdBy"], created_at=d["createdAt"],
                moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
                is_public=d.get("isPublic", False),
            ))
    results.sort(key=lambda c: c.created_at, reverse=True)
    return results


async def update_collection(collection_id: str, data: CollectionUpdate) -> bool:
    if collection_id not in _collections:
        return False
    if data.name is not None:
        _collections[collection_id]["name"] = data.name
    if data.description is not None:
        _collections[collection_id]["description"] = data.description
    if data.is_public is not None:
        _collections[collection_id]["isPublic"] = data.is_public
    return True


async def delete_collection(collection_id: str) -> bool:
    if collection_id not in _collections:
        return False
    del _collections[collection_id]
    return True


async def add_moment_to_collection(collection_id: str, ref: MomentRef) -> bool:
    if collection_id not in _collections:
        return False
    _collections[collection_id].setdefault("momentRefs", []).append(ref.model_dump())
    return True


async def remove_moment_from_collection(collection_id: str, ref: MomentRef) -> bool:
    if collection_id not in _collections:
        return False
    refs = _collections[collection_id].get("momentRefs", [])
    target = ref.model_dump()
    _collections[collection_id]["momentRefs"] = [r for r in refs if r != target]
    return True


# ──────────────────────────── Threads ────────────────────────────

async def upsert_thread(family_id: str, elder_id: str,
                        thread_type: str, name: str,
                        moment_refs: list[MomentRef],
                        session_count: int) -> ThreadResponse:
    now = datetime.now(timezone.utc)
    refs_data = [r.model_dump() for r in moment_refs]

    # Check for existing thread
    for tid, d in _threads.items():
        if (d["familyId"] == family_id and d["elderId"] == elder_id
                and d["type"] == thread_type and d["name"] == name):
            d["momentRefs"] = refs_data
            d["sessionCount"] = session_count
            d["generatedAt"] = now
            return ThreadResponse(
                id=tid, family_id=family_id, elder_id=elder_id,
                type=thread_type, name=name,
                moment_refs=moment_refs,
                generated_at=now, session_count=session_count,
            )

    thread_id = str(uuid.uuid4())
    _threads[thread_id] = {
        "familyId": family_id,
        "elderId": elder_id,
        "type": thread_type,
        "name": name,
        "momentRefs": refs_data,
        "generatedAt": now,
        "sessionCount": session_count,
    }
    return ThreadResponse(
        id=thread_id, family_id=family_id, elder_id=elder_id,
        type=thread_type, name=name, moment_refs=moment_refs,
        generated_at=now, session_count=session_count,
    )


async def list_threads(family_id: str, elder_id: str,
                       thread_type: str = None) -> list[ThreadResponse]:
    results = []
    for tid, d in _threads.items():
        if d["familyId"] != family_id or d["elderId"] != elder_id:
            continue
        if thread_type and d["type"] != thread_type:
            continue
        results.append(ThreadResponse(
            id=tid, family_id=d["familyId"], elder_id=d["elderId"],
            type=d["type"], name=d["name"],
            moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
            generated_at=d["generatedAt"], session_count=d.get("sessionCount", 0),
        ))
    return results


async def get_thread(thread_id: str) -> Optional[ThreadResponse]:
    if thread_id not in _threads:
        return None
    d = _threads[thread_id]
    return ThreadResponse(
        id=thread_id, family_id=d["familyId"], elder_id=d["elderId"],
        type=d["type"], name=d["name"],
        moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
        generated_at=d["generatedAt"], session_count=d.get("sessionCount", 0),
    )


# ──────────────────────────── Books ────────────────────────────

async def create_book(family_id: str, created_by: str,
                      data: BookCreate) -> BookResponse:
    book_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _books[book_id] = {
        "familyId": family_id,
        "elderId": data.elder_id,
        "title": data.title,
        "createdBy": created_by,
        "status": "generating",
        "pdfUrl": "",
        "sourceType": data.source_type,
        "sourceIds": data.source_ids,
        "pageCount": 0,
        "createdAt": now,
    }

    return BookResponse(
        id=book_id, family_id=family_id, elder_id=data.elder_id,
        title=data.title, created_by=created_by, status="generating",
        source_type=data.source_type, source_ids=data.source_ids,
        created_at=now,
    )


async def get_book(book_id: str) -> Optional[BookResponse]:
    if book_id not in _books:
        return None
    d = _books[book_id]
    return BookResponse(
        id=book_id, family_id=d["familyId"], elder_id=d["elderId"],
        title=d["title"], created_by=d["createdBy"],
        status=d["status"], pdf_url=d.get("pdfUrl", ""),
        source_type=d.get("sourceType", "sessions"),
        source_ids=d.get("sourceIds", []),
        page_count=d.get("pageCount", 0),
        created_at=d["createdAt"],
    )


async def update_book(book_id: str, **kwargs) -> None:
    if book_id in _books:
        _books[book_id].update(kwargs)


async def list_books(family_id: str) -> list[BookResponse]:
    results = []
    for bid, d in _books.items():
        if d["familyId"] == family_id:
            results.append(BookResponse(
                id=bid, family_id=d["familyId"], elder_id=d["elderId"],
                title=d["title"], created_by=d["createdBy"],
                status=d["status"], pdf_url=d.get("pdfUrl", ""),
                source_type=d.get("sourceType", "sessions"),
                source_ids=d.get("sourceIds", []),
                page_count=d.get("pageCount", 0),
                created_at=d["createdAt"],
            ))
    results.sort(key=lambda b: b.created_at, reverse=True)
    return results


# ──────────────────────────── Search ────────────────────────────

async def search_moments(elder_id: str, query_text: str = "",
                         tags: list[str] = None, people: list[str] = None,
                         date_from: datetime = None, date_to: datetime = None,
                         channel: str = None,
                         limit: int = 50, offset: int = 0) -> list[dict]:
    """Search moments — in local mode, uses the Phase 1 local_storage sessions/moments."""
    from app.services import local_storage as storage_backend

    sessions = await storage_backend.list_sessions(elder_id=elder_id, limit=1000)
    if channel:
        sessions = [s for s in sessions if s.channel == channel]
    if date_from:
        sessions = [s for s in sessions if s.started_at >= date_from]
    if date_to:
        sessions = [s for s in sessions if s.started_at <= date_to]

    results = []
    for s in sessions:
        moments = await storage_backend.list_moments(s.id)
        for m in moments:
            md = m.model_dump()
            if tags:
                moment_tags = md.get("tags", [])
                if not any(t in moment_tags for t in tags):
                    continue
            if people:
                moment_people = md.get("people_mentioned", [])
                if not any(p.lower() in [mp.lower() for mp in moment_people] for p in people):
                    continue
            if query_text:
                q = query_text.lower()
                searchable = f"{md.get('title', '')} {md.get('summary', '')} {md.get('quote', '')}".lower()
                if q not in searchable:
                    continue
            results.append({
                "moment_id": m.id,
                "session_id": s.id,
                "title": md.get("title", ""),
                "summary": md.get("summary", ""),
                "quote": md.get("quote", ""),
                "emotional_tone": md.get("emotional_tone", ""),
                "image_url": md.get("image_url", ""),
                "tags": md.get("tags", []),
                "people_mentioned": md.get("people_mentioned", []),
                "order": md.get("order", 0),
                "session_date": s.started_at,
                "channel": s.channel,
            })

    results.sort(key=lambda r: r.get("session_date") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return results[offset:offset + limit]


# ──────────────────────────── Migration ────────────────────────────

async def migrate_elder_to_family(elder_id: str) -> Optional[FamilyResponse]:
    from app.services import local_storage as storage_backend
    elder = await storage_backend.get_elder(elder_id)
    if not elder:
        return None

    family = await create_family(
        name=f"{elder.name}'s Family",
        created_by=elder.created_by or "migration",
        elder_ids=[elder_id],
    )
    return family
