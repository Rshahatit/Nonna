"""User, Family, Invite, Collection, Thread, and Book data models for Phase 2."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ──────────────────────────── Users ────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    photo_url: str = ""
    provider: str = "google"
    created_at: datetime


# ──────────────────────────── Families ────────────────────────────

class NotificationPrefs(BaseModel):
    reel_ready: bool = True
    missed_calls: bool = True
    weekly_digest: bool = False
    channel: Literal["sms", "email", "both"] = "sms"


class FamilyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class FamilyResponse(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: datetime
    elder_ids: list[str] = Field(default_factory=list)


class FamilyMemberResponse(BaseModel):
    user_id: str
    role: Literal["organizer", "member", "viewer"]
    joined_at: datetime
    notification_prefs: NotificationPrefs = Field(default_factory=NotificationPrefs)
    name: str = ""
    email: str = ""
    photo_url: str = ""


class FamilyMemberUpdate(BaseModel):
    role: Optional[Literal["organizer", "member", "viewer"]] = None
    notification_prefs: Optional[NotificationPrefs] = None


# ──────────────────────────── Invites ────────────────────────────

class InviteCreate(BaseModel):
    email: Optional[str] = None
    role: Literal["member", "viewer"] = "member"
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InviteResponse(BaseModel):
    id: str
    family_id: str
    email: Optional[str] = None
    role: Literal["member", "viewer"]
    token: str
    created_by: str
    created_at: datetime
    redeemed_at: Optional[datetime] = None
    status: Literal["pending", "redeemed", "expired"] = "pending"
    family_name: str = ""
    inviter_name: str = ""


# ──────────────────────────── Collections ────────────────────────────

class MomentRef(BaseModel):
    session_id: str
    moment_id: str


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    elder_id: str = ""


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class CollectionResponse(BaseModel):
    id: str
    family_id: str
    elder_id: str
    name: str
    description: str = ""
    cover_image_url: str = ""
    created_by: str
    created_at: datetime
    moment_refs: list[MomentRef] = Field(default_factory=list)
    is_public: bool = False


# ──────────────────────────── Threads ────────────────────────────

class ThreadResponse(BaseModel):
    id: str
    family_id: str
    elder_id: str
    type: Literal["person", "place", "theme"]
    name: str
    moment_refs: list[MomentRef] = Field(default_factory=list)
    generated_at: datetime
    session_count: int = 0


# ──────────────────────────── Books ────────────────────────────

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    elder_id: str
    source_type: Literal["sessions", "collection", "custom"] = "sessions"
    source_ids: list[str] = Field(default_factory=list)


class BookResponse(BaseModel):
    id: str
    family_id: str
    elder_id: str
    title: str
    created_by: str
    status: Literal["generating", "preview_ready", "ordered", "shipped"] = "generating"
    pdf_url: str = ""
    source_type: str = "sessions"
    source_ids: list[str] = Field(default_factory=list)
    page_count: int = 0
    created_at: datetime
