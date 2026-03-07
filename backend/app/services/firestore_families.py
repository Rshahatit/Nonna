"""Firestore data access layer for Phase 2: users, families, invites, collections, threads, books."""

from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import secrets

from google.cloud import firestore

from app.services.firestore import get_db
from app.models.user import (
    UserResponse, FamilyResponse, FamilyMemberResponse, FamilyMemberUpdate,
    NotificationPrefs, InviteCreate, InviteResponse,
    CollectionCreate, CollectionResponse, CollectionUpdate, MomentRef,
    ThreadResponse, BookCreate, BookResponse,
)


# ──────────────────────────── Users ────────────────────────────

async def upsert_user(uid: str, email: str, name: str, photo_url: str = "",
                      provider: str = "google") -> UserResponse:
    """Create or update a user document on sign-in."""
    db = get_db()
    now = datetime.now(timezone.utc)
    doc_ref = db.collection("users").document(uid)
    doc = await doc_ref.get()

    if doc.exists:
        await doc_ref.update({
            "name": name,
            "photoUrl": photo_url,
            "lastLoginAt": now,
        })
        d = doc.to_dict()
        return UserResponse(
            id=uid, email=d["email"], name=name,
            photo_url=photo_url, provider=d.get("provider", provider),
            created_at=d["createdAt"],
        )
    else:
        data = {
            "email": email,
            "name": name,
            "photoUrl": photo_url,
            "provider": provider,
            "createdAt": now,
            "lastLoginAt": now,
        }
        await doc_ref.set(data)
        return UserResponse(
            id=uid, email=email, name=name,
            photo_url=photo_url, provider=provider, created_at=now,
        )


async def get_user(uid: str) -> Optional[UserResponse]:
    db = get_db()
    doc = await db.collection("users").document(uid).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    return UserResponse(
        id=uid, email=d["email"], name=d["name"],
        photo_url=d.get("photoUrl", ""), provider=d.get("provider", "google"),
        created_at=d["createdAt"],
    )


async def get_user_by_email(email: str) -> Optional[UserResponse]:
    db = get_db()
    query = db.collection("users").where("email", "==", email).limit(1)
    async for doc in query.stream():
        d = doc.to_dict()
        return UserResponse(
            id=doc.id, email=d["email"], name=d["name"],
            photo_url=d.get("photoUrl", ""), provider=d.get("provider", "google"),
            created_at=d["createdAt"],
        )
    return None


# ──────────────────────────── Families ────────────────────────────

async def create_family(name: str, created_by: str, elder_ids: list[str] = None) -> FamilyResponse:
    db = get_db()
    family_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "name": name,
        "createdBy": created_by,
        "createdAt": now,
        "elderIds": elder_ids or [],
    }
    await db.collection("families").document(family_id).set(doc)

    # Add the creator as organizer
    await db.collection("families").document(family_id).collection("members").document(created_by).set({
        "role": "organizer",
        "joinedAt": now,
        "notificationPrefs": NotificationPrefs().model_dump(),
    })

    return FamilyResponse(
        id=family_id, name=name, created_by=created_by,
        created_at=now, elder_ids=elder_ids or [],
    )


async def get_family(family_id: str) -> Optional[FamilyResponse]:
    db = get_db()
    doc = await db.collection("families").document(family_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    return FamilyResponse(
        id=doc.id, name=d["name"], created_by=d["createdBy"],
        created_at=d["createdAt"], elder_ids=d.get("elderIds", []),
    )


async def update_family(family_id: str, name: str) -> bool:
    db = get_db()
    doc_ref = db.collection("families").document(family_id)
    doc = await doc_ref.get()
    if not doc.exists:
        return False
    await doc_ref.update({"name": name})
    return True


async def add_elder_to_family(family_id: str, elder_id: str) -> bool:
    db = get_db()
    doc_ref = db.collection("families").document(family_id)
    await doc_ref.update({"elderIds": firestore.ArrayUnion([elder_id])})
    # Update elder with familyId
    await db.collection("elders").document(elder_id).update({"familyId": family_id})
    return True


async def list_user_families(user_id: str) -> list[FamilyResponse]:
    """List all families a user belongs to."""
    db = get_db()
    results = []

    # Query all families, then check membership
    # (Firestore doesn't support collection group queries on subcollections easily,
    # so we store a denormalized familyMemberships on the user doc)
    user_doc = await db.collection("users").document(user_id).get()
    if not user_doc.exists:
        return []

    # Alternatively, query using collectionGroup
    query = db.collection_group("members").where(
        firestore.FieldFilter("__name__", ">=", db.document(f"families/x/members/{user_id}"))
    )
    # Simpler approach: iterate families and check membership
    # For scalability, we'd denormalize, but for now:
    async for member_doc in db.collection_group("members").stream():
        if member_doc.id == user_id:
            family_ref = member_doc.reference.parent.parent
            family_doc = await family_ref.get()
            if family_doc.exists:
                d = family_doc.to_dict()
                results.append(FamilyResponse(
                    id=family_doc.id, name=d["name"], created_by=d["createdBy"],
                    created_at=d["createdAt"], elder_ids=d.get("elderIds", []),
                ))
    return results


# ──────────────────────────── Family Members ────────────────────────────

async def get_family_member(family_id: str, user_id: str) -> Optional[FamilyMemberResponse]:
    db = get_db()
    doc = await db.collection("families").document(family_id).collection("members").document(user_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()

    # Get user info
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
    db = get_db()
    members = []
    query = db.collection("families").document(family_id).collection("members")
    async for doc in query.stream():
        d = doc.to_dict()
        user = await get_user(doc.id)
        members.append(FamilyMemberResponse(
            user_id=doc.id,
            role=d["role"],
            joined_at=d["joinedAt"],
            notification_prefs=NotificationPrefs(**d.get("notificationPrefs", {})),
            name=user.name if user else "",
            email=user.email if user else "",
            photo_url=user.photo_url if user else "",
        ))
    return members


async def update_family_member(family_id: str, user_id: str,
                                update: FamilyMemberUpdate) -> bool:
    db = get_db()
    doc_ref = db.collection("families").document(family_id).collection("members").document(user_id)
    doc = await doc_ref.get()
    if not doc.exists:
        return False

    updates = {}
    if update.role is not None:
        updates["role"] = update.role
    if update.notification_prefs is not None:
        updates["notificationPrefs"] = update.notification_prefs.model_dump()
    if updates:
        await doc_ref.update(updates)
    return True


async def remove_family_member(family_id: str, user_id: str) -> bool:
    db = get_db()
    doc_ref = db.collection("families").document(family_id).collection("members").document(user_id)
    doc = await doc_ref.get()
    if not doc.exists:
        return False
    await doc_ref.delete()
    return True


async def add_family_member(family_id: str, user_id: str, role: str = "member") -> FamilyMemberResponse:
    db = get_db()
    now = datetime.now(timezone.utc)
    prefs = NotificationPrefs()
    await db.collection("families").document(family_id).collection("members").document(user_id).set({
        "role": role,
        "joinedAt": now,
        "notificationPrefs": prefs.model_dump(),
    })
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
    db = get_db()
    invite_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    family = await get_family(family_id)
    creator = await get_user(created_by)

    doc = {
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
    await db.collection("invites").document(invite_id).set(doc)

    return InviteResponse(
        id=invite_id, family_id=family_id, email=data.email,
        role=data.role, token=token, created_by=created_by,
        created_at=now, status="pending",
        family_name=family.name if family else "",
        inviter_name=creator.name if creator else "",
    )


async def get_invite_by_token(token: str) -> Optional[InviteResponse]:
    db = get_db()
    query = db.collection("invites").where("token", "==", token).limit(1)
    async for doc in query.stream():
        d = doc.to_dict()
        now = datetime.now(timezone.utc)

        # Check expiry
        status = d["status"]
        if status == "pending" and d.get("expiresAt") and d["expiresAt"] < now:
            status = "expired"
            await doc.reference.update({"status": "expired"})

        family = await get_family(d["familyId"])
        creator = await get_user(d["createdBy"])

        return InviteResponse(
            id=doc.id, family_id=d["familyId"], email=d.get("email"),
            role=d["role"], token=d["token"], created_by=d["createdBy"],
            created_at=d["createdAt"], redeemed_at=d.get("redeemedAt"),
            status=status,
            family_name=family.name if family else "",
            inviter_name=creator.name if creator else "",
        )
    return None


async def redeem_invite(token: str, user_id: str) -> Optional[FamilyMemberResponse]:
    """Redeem an invite token, adding the user to the family."""
    invite = await get_invite_by_token(token)
    if not invite:
        return None
    if invite.status != "pending":
        return None

    # Check if already a member
    existing = await get_family_member(invite.family_id, user_id)
    if existing:
        return existing

    # Add member
    member = await add_family_member(invite.family_id, user_id, invite.role)

    # Mark invite as redeemed
    db = get_db()
    now = datetime.now(timezone.utc)
    query = db.collection("invites").where("token", "==", token).limit(1)
    async for doc in query.stream():
        await doc.reference.update({"status": "redeemed", "redeemedAt": now})

    return member


async def list_family_invites(family_id: str) -> list[InviteResponse]:
    db = get_db()
    invites = []
    query = db.collection("invites").where("familyId", "==", family_id).order_by(
        "createdAt", direction=firestore.Query.DESCENDING
    )
    async for doc in query.stream():
        d = doc.to_dict()
        family = await get_family(d["familyId"])
        creator = await get_user(d["createdBy"])
        invites.append(InviteResponse(
            id=doc.id, family_id=d["familyId"], email=d.get("email"),
            role=d["role"], token=d["token"], created_by=d["createdBy"],
            created_at=d["createdAt"], redeemed_at=d.get("redeemedAt"),
            status=d["status"],
            family_name=family.name if family else "",
            inviter_name=creator.name if creator else "",
        ))
    return invites


async def revoke_invite(invite_id: str) -> bool:
    db = get_db()
    doc_ref = db.collection("invites").document(invite_id)
    doc = await doc_ref.get()
    if not doc.exists:
        return False
    if doc.to_dict()["status"] != "pending":
        return False
    await doc_ref.update({"status": "expired"})
    return True


# ──────────────────────────── Collections ────────────────────────────

async def create_collection(family_id: str, created_by: str,
                            data: CollectionCreate) -> CollectionResponse:
    db = get_db()
    collection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
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
    await db.collection("collections").document(collection_id).set(doc)

    return CollectionResponse(
        id=collection_id, family_id=family_id, elder_id=data.elder_id,
        name=data.name, description=data.description,
        created_by=created_by, created_at=now,
    )


async def get_collection(collection_id: str) -> Optional[CollectionResponse]:
    db = get_db()
    doc = await db.collection("collections").document(collection_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    return CollectionResponse(
        id=doc.id, family_id=d["familyId"], elder_id=d.get("elderId", ""),
        name=d["name"], description=d.get("description", ""),
        cover_image_url=d.get("coverImageUrl", ""),
        created_by=d["createdBy"], created_at=d["createdAt"],
        moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
        is_public=d.get("isPublic", False),
    )


async def list_collections(family_id: str) -> list[CollectionResponse]:
    db = get_db()
    results = []
    query = db.collection("collections").where("familyId", "==", family_id).order_by(
        "createdAt", direction=firestore.Query.DESCENDING
    )
    async for doc in query.stream():
        d = doc.to_dict()
        results.append(CollectionResponse(
            id=doc.id, family_id=d["familyId"], elder_id=d.get("elderId", ""),
            name=d["name"], description=d.get("description", ""),
            cover_image_url=d.get("coverImageUrl", ""),
            created_by=d["createdBy"], created_at=d["createdAt"],
            moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
            is_public=d.get("isPublic", False),
        ))
    return results


async def update_collection(collection_id: str, data: CollectionUpdate) -> bool:
    db = get_db()
    doc_ref = db.collection("collections").document(collection_id)
    doc = await doc_ref.get()
    if not doc.exists:
        return False
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.description is not None:
        updates["description"] = data.description
    if data.is_public is not None:
        updates["isPublic"] = data.is_public
    if updates:
        await doc_ref.update(updates)
    return True


async def delete_collection(collection_id: str) -> bool:
    db = get_db()
    doc_ref = db.collection("collections").document(collection_id)
    doc = await doc_ref.get()
    if not doc.exists:
        return False
    await doc_ref.delete()
    return True


async def add_moment_to_collection(collection_id: str, ref: MomentRef) -> bool:
    db = get_db()
    doc_ref = db.collection("collections").document(collection_id)
    await doc_ref.update({
        "momentRefs": firestore.ArrayUnion([ref.model_dump()])
    })
    return True


async def remove_moment_from_collection(collection_id: str, ref: MomentRef) -> bool:
    db = get_db()
    doc_ref = db.collection("collections").document(collection_id)
    await doc_ref.update({
        "momentRefs": firestore.ArrayRemove([ref.model_dump()])
    })
    return True


# ──────────────────────────── Threads ────────────────────────────

async def upsert_thread(family_id: str, elder_id: str,
                        thread_type: str, name: str,
                        moment_refs: list[MomentRef],
                        session_count: int) -> ThreadResponse:
    """Create or update a thread. If one exists with same type+name, update it."""
    db = get_db()
    now = datetime.now(timezone.utc)

    # Check for existing thread
    query = db.collection("threads").where("familyId", "==", family_id).where(
        "elderId", "==", elder_id
    ).where("type", "==", thread_type).where("name", "==", name).limit(1)

    existing_doc = None
    async for doc in query.stream():
        existing_doc = doc

    refs_data = [r.model_dump() for r in moment_refs]

    if existing_doc:
        await existing_doc.reference.update({
            "momentRefs": refs_data,
            "sessionCount": session_count,
            "generatedAt": now,
        })
        return ThreadResponse(
            id=existing_doc.id, family_id=family_id, elder_id=elder_id,
            type=thread_type, name=name, moment_refs=moment_refs,
            generated_at=now, session_count=session_count,
        )
    else:
        thread_id = str(uuid.uuid4())
        doc = {
            "familyId": family_id,
            "elderId": elder_id,
            "type": thread_type,
            "name": name,
            "momentRefs": refs_data,
            "generatedAt": now,
            "sessionCount": session_count,
        }
        await db.collection("threads").document(thread_id).set(doc)
        return ThreadResponse(
            id=thread_id, family_id=family_id, elder_id=elder_id,
            type=thread_type, name=name, moment_refs=moment_refs,
            generated_at=now, session_count=session_count,
        )


async def list_threads(family_id: str, elder_id: str,
                       thread_type: str = None) -> list[ThreadResponse]:
    db = get_db()
    query = db.collection("threads").where(
        "familyId", "==", family_id
    ).where("elderId", "==", elder_id)
    if thread_type:
        query = query.where("type", "==", thread_type)

    results = []
    async for doc in query.stream():
        d = doc.to_dict()
        results.append(ThreadResponse(
            id=doc.id, family_id=d["familyId"], elder_id=d["elderId"],
            type=d["type"], name=d["name"],
            moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
            generated_at=d["generatedAt"], session_count=d.get("sessionCount", 0),
        ))
    return results


async def get_thread(thread_id: str) -> Optional[ThreadResponse]:
    db = get_db()
    doc = await db.collection("threads").document(thread_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    return ThreadResponse(
        id=doc.id, family_id=d["familyId"], elder_id=d["elderId"],
        type=d["type"], name=d["name"],
        moment_refs=[MomentRef(**m) for m in d.get("momentRefs", [])],
        generated_at=d["generatedAt"], session_count=d.get("sessionCount", 0),
    )


# ──────────────────────────── Books ────────────────────────────

async def create_book(family_id: str, created_by: str,
                      data: BookCreate) -> BookResponse:
    db = get_db()
    book_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
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
    await db.collection("books").document(book_id).set(doc)

    return BookResponse(
        id=book_id, family_id=family_id, elder_id=data.elder_id,
        title=data.title, created_by=created_by, status="generating",
        source_type=data.source_type, source_ids=data.source_ids,
        created_at=now,
    )


async def get_book(book_id: str) -> Optional[BookResponse]:
    db = get_db()
    doc = await db.collection("books").document(book_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    return BookResponse(
        id=doc.id, family_id=d["familyId"], elder_id=d["elderId"],
        title=d["title"], created_by=d["createdBy"],
        status=d["status"], pdf_url=d.get("pdfUrl", ""),
        source_type=d.get("sourceType", "sessions"),
        source_ids=d.get("sourceIds", []),
        page_count=d.get("pageCount", 0),
        created_at=d["createdAt"],
    )


async def update_book(book_id: str, **kwargs) -> None:
    db = get_db()
    await db.collection("books").document(book_id).update(kwargs)


async def list_books(family_id: str) -> list[BookResponse]:
    db = get_db()
    results = []
    query = db.collection("books").where("familyId", "==", family_id).order_by(
        "createdAt", direction=firestore.Query.DESCENDING
    )
    async for doc in query.stream():
        d = doc.to_dict()
        results.append(BookResponse(
            id=doc.id, family_id=d["familyId"], elder_id=d["elderId"],
            title=d["title"], created_by=d["createdBy"],
            status=d["status"], pdf_url=d.get("pdfUrl", ""),
            source_type=d.get("sourceType", "sessions"),
            source_ids=d.get("sourceIds", []),
            page_count=d.get("pageCount", 0),
            created_at=d["createdAt"],
        ))
    return results


# ──────────────────────────── Search ────────────────────────────

async def search_moments(elder_id: str, query_text: str = "",
                         tags: list[str] = None, people: list[str] = None,
                         date_from: datetime = None, date_to: datetime = None,
                         channel: str = None,
                         limit: int = 50, offset: int = 0) -> list[dict]:
    """Search moments across all sessions for an elder."""
    db = get_db()

    # Get all sessions for this elder
    sessions_query = db.collection("sessions").where("elderId", "==", elder_id)
    if channel:
        sessions_query = sessions_query.where("channel", "==", channel)

    session_ids = []
    session_map = {}
    async for doc in sessions_query.stream():
        d = doc.to_dict()
        started = d["startedAt"]
        if date_from and started < date_from:
            continue
        if date_to and started > date_to:
            continue
        session_ids.append(doc.id)
        session_map[doc.id] = d

    results = []
    for sid in session_ids:
        moments_query = db.collection("sessions").document(sid).collection("moments")
        async for mdoc in moments_query.stream():
            m = mdoc.to_dict()

            # Filter by tags
            if tags:
                moment_tags = m.get("tags", [])
                if not any(t in moment_tags for t in tags):
                    continue

            # Filter by people
            if people:
                moment_people = m.get("peopleMentioned", [])
                if not any(p.lower() in [mp.lower() for mp in moment_people] for p in people):
                    continue

            # Filter by search text
            if query_text:
                q = query_text.lower()
                searchable = f"{m.get('title', '')} {m.get('summary', '')} {m.get('quote', '')}".lower()
                if q not in searchable:
                    continue

            session_data = session_map.get(sid, {})
            results.append({
                "moment_id": mdoc.id,
                "session_id": sid,
                "title": m.get("title", ""),
                "summary": m.get("summary", ""),
                "quote": m.get("quote", ""),
                "emotional_tone": m.get("emotional_tone", ""),
                "image_url": m.get("image_url", ""),
                "tags": m.get("tags", []),
                "people_mentioned": m.get("peopleMentioned", []),
                "place_mentioned": m.get("placeMentioned"),
                "order": m.get("order", 0),
                "session_date": session_data.get("startedAt"),
                "channel": session_data.get("channel", ""),
            })

    # Sort by session date descending
    results.sort(key=lambda r: r.get("session_date") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return results[offset:offset + limit]


# ──────────────────────────── Migration ────────────────────────────

async def migrate_elder_to_family(elder_id: str) -> Optional[FamilyResponse]:
    """Wrap an existing Phase 1 elder in a family group.

    The elder's createdBy becomes the organizer. Idempotent.
    """
    db = get_db()
    elder_doc = await db.collection("elders").document(elder_id).get()
    if not elder_doc.exists:
        return None

    d = elder_doc.to_dict()

    # Check if already migrated
    if d.get("familyId"):
        return await get_family(d["familyId"])

    # Create a family
    elder_name = d["name"]
    family_name = f"{elder_name}'s Family"
    created_by = d.get("createdBy", "")

    # We need a user record for the creator. If they signed in with Google,
    # they'll have one. For migration, create a placeholder if needed.
    family = await create_family(
        name=family_name,
        created_by=created_by or "migration",
        elder_ids=[elder_id],
    )

    # Update elder with family ID
    await db.collection("elders").document(elder_id).update({"familyId": family.id})

    return family
