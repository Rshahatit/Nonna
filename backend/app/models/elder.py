"""Elder data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CallSchedule(BaseModel):
    days: list[str] = Field(default_factory=list, description="Days of week, e.g. ['monday', 'wednesday']")
    time: str = Field(default="14:00", description="Time in HH:MM format")
    timezone: str = Field(default="America/New_York")


class PersonMentioned(BaseModel):
    name: str
    relationship: str = ""
    first_mentioned: Optional[str] = None
    details: list[str] = Field(default_factory=list)


class PlaceMentioned(BaseModel):
    name: str
    significance: str = ""
    stories: list[str] = Field(default_factory=list)


class LifeEvent(BaseModel):
    event: str
    approximate_date: str = ""
    details: str = ""


class RecipeOrSkill(BaseModel):
    name: str
    description: str = ""
    session_id: str = ""


class ElderMemory(BaseModel):
    people: list[PersonMentioned] = Field(default_factory=list)
    places: list[PlaceMentioned] = Field(default_factory=list)
    life_events: list[LifeEvent] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    recipes_and_skills: list[RecipeOrSkill] = Field(default_factory=list)
    story_gaps: list[str] = Field(default_factory=list)
    session_count: int = 0
    last_session_date: Optional[datetime] = None
    conversation_style: str = ""


class ElderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    seed_context: str = Field(default="", max_length=5000)
    call_schedule: CallSchedule = Field(default_factory=CallSchedule)
    created_by: str = Field(default="", description="Family member identifier (phone or email)")


class ElderUpdate(BaseModel):
    name: Optional[str] = None
    seed_context: Optional[str] = None
    call_schedule: Optional[CallSchedule] = None


class ElderResponse(BaseModel):
    id: str
    name: str
    phone_number: str
    seed_context: str
    call_schedule: CallSchedule
    created_at: datetime
    created_by: str


class ElderScheduleUpdate(BaseModel):
    call_schedule: CallSchedule
