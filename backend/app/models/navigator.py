"""Navigator and session mode data models for Phase 3."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


SessionMode = Literal["story", "navigator", "check_in", "assist"]


class ModeTransition(BaseModel):
    from_mode: SessionMode
    to_mode: SessionMode
    timestamp: datetime


class NavigationContext(BaseModel):
    task: Optional[str] = None
    current_app: Optional[str] = None
    current_screen: Optional[str] = None
    steps_completed: list[str] = Field(default_factory=list)
    steps_remaining: list[str] = Field(default_factory=list)
    screens_analyzed: int = 0
    task_completed: bool = False
    stuck_count: int = 0


class ScreenAnalysis(BaseModel):
    app_name: str = ""
    screen_description: str = ""
    ui_elements: list[str] = Field(default_factory=list)
    suggested_action: str = ""
    instruction_text: str = ""
    is_same_as_previous: bool = False


class CheckInLog(BaseModel):
    id: str = ""
    elder_id: str = ""
    session_id: str = ""
    date: datetime
    mood: Optional[str] = None
    topics_discussed: list[str] = Field(default_factory=list)
    transitioned_to: Optional[str] = None
    duration: Optional[int] = None


class AssistLog(BaseModel):
    id: str = ""
    elder_id: str = ""
    session_id: str = ""
    date: datetime
    task: str = ""
    task_completed: bool = False
    screens_analyzed: int = 0
    duration: Optional[int] = None


class OnboardingStatus(BaseModel):
    pwa_setup: bool = False
    home_screen_added: bool = False
    camera_permission_granted: bool = False
    mic_permission_granted: bool = False
    completed_at: Optional[datetime] = None


class AccessibilityPrefs(BaseModel):
    font_size: Literal["normal", "large", "extra_large"] = "normal"
    high_contrast: bool = False
    reduced_motion: bool = False
    touch_target_size: Literal["normal", "large"] = "normal"


class CheckInSchedule(BaseModel):
    enabled: bool = False
    type: Literal["morning", "afternoon", "both"] = "morning"
    time: str = "09:00"
    timezone: str = "America/New_York"
