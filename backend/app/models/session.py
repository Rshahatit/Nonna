"""Session and Moment data models."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

from app.models.navigator import SessionMode, ModeTransition, NavigationContext


class SessionCreate(BaseModel):
    elder_id: str
    channel: Literal["phone", "pwa"]
    mode: SessionMode = "story"


class SessionResponse(BaseModel):
    id: str
    elder_id: str
    channel: Literal["phone", "pwa"]
    status: Literal["live", "processing", "complete", "failed"]
    mode: SessionMode = "story"
    mode_transitions: list[ModeTransition] = Field(default_factory=list)
    navigation_context: Optional[NavigationContext] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    transcript_url: str = ""
    vision_context_used: bool = False
    topics_covered: list[str] = Field(default_factory=list)
    new_people_mentioned: list[str] = Field(default_factory=list)


class MomentResponse(BaseModel):
    id: str
    title: str
    summary: str
    quote: str
    visual_description: str
    emotional_tone: str
    image_url: str = ""
    order: int = 0
    # Phase 2 fields
    tags: list[str] = Field(default_factory=list)
    people_mentioned: list[str] = Field(default_factory=list)
    place_mentioned: Optional[str] = None


class ReelResponse(BaseModel):
    id: str
    session_id: str
    elder_id: str
    status: Literal["generating", "ready", "failed"]
    video_url: str = ""
    thumbnail_url: str = ""
    duration: Optional[int] = None
    created_at: datetime
