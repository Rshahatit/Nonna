"""In-memory storage backend for Phase 2 families, mirroring firestore_families.py.

Used for local development when USE_LOCAL_STORAGE=true.
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
_family_members: dict[str, dict[str, dict]] = {}  # family_id -> {user_id -> data}
_invites: dict[str, dict] = {}
_collections: dict[str, dict] = {}
_threads: dict[str, dict] = {}
_books: dict[str, dict] = {}


def get_db():
    return None


# ──────────────────────────── Users ────────────────────────────

async def upsert_user(uid: str, email: str, name: str, photo_url: str = "",
                      provider: str = "google") -> UserResponse:
    now = datetime.now(timezone.utc)
    if uid in _users:
        _users[uid]["name"] = name
        _users[uid]["photoUrl"] = photo_url
        _users[uid]["lastLoginAt"] = now
        d = _users[uid]
        return UserResponse(
            id=uid, email=d["email"], name=name,
            photo_url=photo_url, provider=d.get("provider", provider),
            created_at=d["createdAt"],
        )
    else:
        _users[uid] = {
            "email": email, "name": name, "photoUrl": photo_url,
            "provider": provider, "createdAt": now, "lastLoginAt": now,
        }
        return UserResponse(
            id=uid, email=email, name=name,
            photo_url=photo_url, provider=provider, created_at=now,
        )


async def get_user(uid: str) -> Optional[UserResponse]:
    d = _users.get(uid)
    if not d:
        return None
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
        "name": name, "createdBy": created_by,
        "createdAt": now, "elderIds": elder_ids or [],
    }
    _family_members[family_id] = {
        created_by: {
            "role": "organizer", "joinedAt": now,
            "notificationPrefs": NotificationPrefs().model_dump(),
        }
    }
    return FamilyResponse(
        id=family_id, name=name, created_by=created_by,
        created_at=now, elder_ids=elder_ids or [],
    )


async def get_family(family_id: str) -> Optional[FamilyResponse]:
    d = _families.get(family_id)
    if not d:
        return None
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
    eids = _families[family_id].setdefault("elderIds", [])
    if elder_id not in eids:
        eids.append(elder_id)
    from app.services.local_storage import _elders
    if elder_id in _elders:
        _elders[elder_id]["familyId"] = family_id
    return True


async def list_user_families(user_id: str) -> list[FamilyResponse]:
    results = []
    for fid, members in _family_members.items():
        if user_id in members:
            d = _families.get(fid)
            if d:
                results.append(FamilyResponse(
                    id=fid, name=d["name"], created_by=d["createdBy"],
                    created_at=d["createdAt"], elder_ids=d.get("elderIds", []),
                ))
    return results


# ──────────────────────────── Family Members ────────────────────────────

async def get_family_member(family_id: str, user_id: str) -> Optional[FamilyMemberResponse]:
    members = _family_members.get(family_id, {})
    d = members.get(user_id)
    if not d:
        return None
    user = await get_user(user_id)
    return FamilyMemberResponse(
        user_id=user_id, role=d["role"], joined_at=d["joinedAt"],
        notification_prefs=NotificationPrefs(**d.get("notificationPrefs", {})),
        name=user.name if user else "", email=user.email if user else "",
        photo_url=user.photo_url if user else "",
    )


async def list_family_members(family_id: str) -> list[FamilyMemberResponse]:
    members = _family_members.get(family_id, {})
    results = []
    for uid, d in members.items():
        user = await get_user(uid)
        results.append(FamilyMemberResponse(
            user_id=uid, role=d["role"], joined_at=d["joinedAt"],
            notification_prefs=NotificationPrefs(**d.get("notificationPrefs", {})),
            name=user.name if user else "", email=user.email if user else "",
            photo_url=user.photo_url if user else "",
        ))
    return results


async def update_family_member(family_id: str, user_id: str, update: FamilyMemberUpdate) -> bool:
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
        "role": role, "joinedAt": now,
        "notificationPrefs": prefs.model_dump(),
    }
    user = await get_user(user_id)
    return FamilyMemberResponse(
        user_id=user_id, role=role, joined_at=now,
        notification_prefs=prefs,
        name=user.name if user else "", email=user.email if user else "",
        photo_url=user.photo_url if user else "",
    )


# ──────────────────────────── Invites ────────────────────────────

async def create_invite(family_id: str, created_by: str, data: InviteCreate) -> InviteResponse:
    invite_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    family = await get_family(family_id)
    creator = await get_user(created_by)

    _invites[invite_id] = {
        "familyId": family_id, "email": data.email, "role": data.role,
        "token": token, "createdBy": created_by, "createdAt": now,
        "expiresAt": now + timedelta(days=data.expires_in_days),
        "redeemedAt": None, "status": "pending",
    }
    return InviteResponse(
        id=invite_id, family_id=family_id, email=data.email,
        role=data.role, token=token, created_by=created_by,
        created_at=now, status="pending",
        family_name=family.name if family else "",
        inviter_name=creator.name if creator else "",
    )


async def get_invite_by_token(token: str) -> Optional[InviteResponse]:
    for iid, d in _invites.items():
        if d["token"] == token:
            now = datetime.now(timezone.utc)
            status = d["status"]
            if status == "pending" and d.get("expiresAt") and d["expiresAt"] < now:
                status = "expired"
                d["status"] = "expired"
            family = await get_family(d["familyId"])
            creator = await get_user(d["createdBy"])
            return InviteResponse(
                id=iid, family_id=d["familyId"], email=d.get("email"),
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
    for d in _invites.values():
        if d["token"] == token:
            d["status"] = "redeemed"
            d["redeemedAt"] = now
            break
    return member


async def list_family_invites(family_id: str) -> list[InviteResponse]:
    results = []
    for iid, d in _invites.items():
        if d["familyId"] == family_id:
            family = await get_family(d["familyId"])
            creator = await get_user(d["createdBy"])
            results.append(InviteResponse(
                id=iid, family_id=d["familyId"], email=d.get("email"),
                role=d["role"], token=d["token"], created_by=d["createdBy"],
                created_at=d["createdAt"], redeemed_at=d.get("redeemedAt"),
                status=d["status"],
                family_name=family.name if family else "",
                inviter_name=creator.name if creator else "",
            ))
    results.sort(key=lambda i: i.created_at, reverse=True)
    return results


async def revoke_invite(invite_id: str) -> bool:
    d = _invites.get(invite_id)
    if not d or d["status"] != "pending":
        return False
    d["status"] = "expired"
    return True


# ──────────────────────────── Collections ────────────────────────────

async def create_collection(family_id: str, created_by: str, data: CollectionCreate) -> CollectionResponse:
    collection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    _collections[collection_id] = {
        "familyId": family_id, "elderId": data.elder_id,
        "name": data.name, "description": data.description,
        "coverImageUrl": "", "createdBy": created_by,
        "createdAt": now, "momentRefs": [], "isPublic": False,
    }
    return CollectionResponse(
        id=collection_id, family_id=family_id, elder_id=data.elder_id,
        name=data.name, description=data.description,
        created_by=created_by, created_at=now,
    )


async def get_collection(collection_id: str) -> Optional[CollectionResponse]:
    d = _collections.get(collection_id)
    if not d:
        return None
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
    d = _collections.get(collection_id)
    if not d:
        return False
    if data.name is not None:
        d["name"] = data.name
    if data.description is not None:
        d["description"] = data.description
    if data.is_public is not None:
        d["isPublic"] = data.is_public
    return True


async def delete_collection(collection_id: str) -> bool:
    if collection_id not in _collections:
        return False
    del _collections[collection_id]
    return True


async def add_moment_to_collection(collection_id: str, ref: MomentRef) -> bool:
    d = _collections.get(collection_id)
    if not d:
        return False
    d["momentRefs"].append(ref.model_dump())
    return True


async def remove_moment_from_collection(collection_id: str, ref: MomentRef) -> bool:
    d = _collections.get(collection_id)
    if not d:
        return False
    ref_dict = ref.model_dump()
    d["momentRefs"] = [m for m in d["momentRefs"] if m != ref_dict]
    return True


# ──────────────────────────── Threads ────────────────────────────

async def upsert_thread(family_id: str, elder_id: str,
                        thread_type: str, name: str,
                        moment_refs: list[MomentRef],
                        session_count: int) -> ThreadResponse:
    now = datetime.now(timezone.utc)
    refs_data = [r.model_dump() for r in moment_refs]

    for tid, d in _threads.items():
        if (d["familyId"] == family_id and d["elderId"] == elder_id
                and d["type"] == thread_type and d["name"] == name):
            d["momentRefs"] = refs_data
            d["sessionCount"] = session_count
            d["generatedAt"] = now
            return ThreadResponse(
                id=tid, family_id=family_id, elder_id=elder_id,
                type=thread_type, name=name, moment_refs=moment_refs,
                generated_at=now, session_count=session_count,
            )

    thread_id = str(uuid.uuid4())
    _threads[thread_id] = {
        "familyId": family_id, "elderId": elder_id,
        "type": thread_type, "name": name,
        "momentRefs": refs_data, "generatedAt": now,
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
        if d["familyId"] == family_id and d["elderId"] == elder_id:
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
    d = _threads.get(thread_id)
    if not d:
        return None
    return ThreadResponse(
        id=thread_id, family_id=d["familyId"], elder_id=d["elderId"],
        type=d["type"], name=d["name"],
        moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
        generated_at=d["generatedAt"], session_count=d.get("sessionCount", 0),
    )


# ──────────────────────────── Books ────────────────────────────

async def create_book(family_id: str, created_by: str, data: BookCreate) -> BookResponse:
    book_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    _books[book_id] = {
        "familyId": family_id, "elderId": data.elder_id,
        "title": data.title, "createdBy": created_by,
        "status": "generating", "pdfUrl": "",
        "sourceType": data.source_type, "sourceIds": data.source_ids,
        "pageCount": 0, "createdAt": now,
    }
    return BookResponse(
        id=book_id, family_id=family_id, elder_id=data.elder_id,
        title=data.title, created_by=created_by, status="generating",
        source_type=data.source_type, source_ids=data.source_ids,
        created_at=now,
    )


async def get_book(book_id: str) -> Optional[BookResponse]:
    d = _books.get(book_id)
    if not d:
        return None
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
    from app.services.local_storage import _sessions, _moments

    session_ids = []
    session_map = {}
    for sid, d in _sessions.items():
        if d["elderId"] != elder_id:
            continue
        if channel and d["channel"] != channel:
            continue
        started = d["startedAt"]
        if date_from and started < date_from:
            continue
        if date_to and started > date_to:
            continue
        session_ids.append(sid)
        session_map[sid] = d

    results = []
    for sid in session_ids:
        for mid, m in _moments.get(sid, {}).items():
            if tags:
                moment_tags = m.get("tags", [])
                if not any(t in moment_tags for t in tags):
                    continue
            if people:
                moment_people = m.get("peopleMentioned", [])
                if not any(p.lower() in [mp.lower() for mp in moment_people] for p in people):
                    continue
            if query_text:
                q = query_text.lower()
                searchable = f"{m.get('title', '')} {m.get('summary', '')} {m.get('quote', '')}".lower()
                if q not in searchable:
                    continue
            session_data = session_map.get(sid, {})
            results.append({
                "moment_id": mid, "session_id": sid,
                "title": m.get("title", ""), "summary": m.get("summary", ""),
                "quote": m.get("quote", ""), "emotional_tone": m.get("emotional_tone", ""),
                "image_url": m.get("image_url", ""),
                "tags": m.get("tags", []), "people_mentioned": m.get("peopleMentioned", []),
                "place_mentioned": m.get("placeMentioned"),
                "order": m.get("order", 0),
                "session_date": session_data.get("startedAt"),
                "channel": session_data.get("channel", ""),
            })

    results.sort(key=lambda r: r.get("session_date") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return results[offset:offset + limit]


# ──────────────────────────── Migration ────────────────────────────

async def migrate_elder_to_family(elder_id: str) -> Optional[FamilyResponse]:
    from app.services.local_storage import _elders
    d = _elders.get(elder_id)
    if not d:
        return None
    if d.get("familyId"):
        return await get_family(d["familyId"])
    elder_name = d["name"]
    family_name = f"{elder_name}'s Family"
    created_by = d.get("createdBy", "")
    family = await create_family(
        name=family_name,
        created_by=created_by or "migration",
        elder_ids=[elder_id],
    )
    d["familyId"] = family.id
    return family
