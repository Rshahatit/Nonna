"""Tests for Pydantic data models."""

from datetime import datetime
import pytest
from app.models.elder import (
    CallSchedule,
    PersonMentioned,
    PlaceMentioned,
    LifeEvent,
    RecipeOrSkill,
    ElderMemory,
    ElderCreate,
    ElderUpdate,
    ElderResponse,
    ElderScheduleUpdate,
)
from app.models.session import (
    SessionCreate,
    SessionResponse,
    MomentResponse,
    ReelResponse,
)


class TestCallSchedule:
    def test_valid_schedule(self):
        schedule = CallSchedule(days=["tuesday", "thursday"], time="14:00", timezone="America/New_York")
        assert schedule.days == ["tuesday", "thursday"]
        assert schedule.time == "14:00"
        assert schedule.timezone == "America/New_York"

    def test_empty_days(self):
        schedule = CallSchedule(days=[], time="10:00", timezone="UTC")
        assert schedule.days == []


class TestPersonMentioned:
    def test_create_person(self):
        person = PersonMentioned(
            name="Samir",
            relationship="brother",
            first_mentioned="session_001",
            details=["Grew up together in Amman", "Loved playing soccer"],
        )
        assert person.name == "Samir"
        assert person.relationship == "brother"
        assert len(person.details) == 2


class TestPlaceMentioned:
    def test_create_place(self):
        place = PlaceMentioned(
            name="Amman",
            significance="Hometown where she grew up",
            stories=["Walking to school", "The old market"],
        )
        assert place.name == "Amman"
        assert len(place.stories) == 2


class TestLifeEvent:
    def test_create_event(self):
        event = LifeEvent(
            event="Wedding",
            approximate_date="1975",
            details="Married Hassan in a big ceremony in Amman",
        )
        assert event.event == "Wedding"


class TestRecipeOrSkill:
    def test_create_recipe(self):
        recipe = RecipeOrSkill(
            name="Baklava",
            description="Grandmother's layered pastry with pistachios and rose water",
            session_id="session_003",
        )
        assert recipe.name == "Baklava"


class TestElderMemory:
    def test_default_memory(self):
        memory = ElderMemory()
        assert memory.people == []
        assert memory.places == []
        assert memory.life_events == []
        assert memory.themes == []
        assert memory.recipes_and_skills == []
        assert memory.story_gaps == []
        assert memory.session_count == 0
        assert memory.conversation_style == ""

    def test_populated_memory(self):
        memory = ElderMemory(
            people=[PersonMentioned(name="Samir", relationship="brother", first_mentioned="s1", details=[])],
            places=[PlaceMentioned(name="Amman", significance="Home", stories=[])],
            themes=["family", "cooking"],
            session_count=5,
            conversation_style="loves tangents, very warm",
        )
        assert len(memory.people) == 1
        assert len(memory.themes) == 2
        assert memory.session_count == 5


class TestElderCreate:
    def test_create_elder(self):
        elder = ElderCreate(
            name="Fatima",
            phone_number="+12025551234",
            seed_context="Mom grew up in Amman, amazing cook, dad passed 2 years ago",
            created_by="+12025559999",
        )
        assert elder.name == "Fatima"
        assert elder.phone_number == "+12025551234"

    def test_optional_schedule(self):
        elder = ElderCreate(
            name="Fatima",
            phone_number="+12025551234",
            seed_context="Loves gardening",
            created_by="+12025559999",
            call_schedule=CallSchedule(days=["monday"], time="10:00", timezone="UTC"),
        )
        assert elder.call_schedule is not None
        assert elder.call_schedule.days == ["monday"]


class TestElderUpdate:
    def test_partial_update(self):
        update = ElderUpdate(name="Fatima Al-Hassan")
        assert update.name == "Fatima Al-Hassan"
        assert update.seed_context is None

    def test_all_none(self):
        update = ElderUpdate()
        assert update.name is None
        assert update.seed_context is None


class TestElderResponse:
    def test_response(self):
        resp = ElderResponse(
            id="elder_123",
            name="Fatima",
            phone_number="+12025551234",
            seed_context="Loves cooking",
            created_by="+12025559999",
            created_at=datetime(2024, 1, 1),
            call_schedule=CallSchedule(),
        )
        assert resp.id == "elder_123"


class TestSessionCreate:
    def test_phone_channel(self):
        session = SessionCreate(elder_id="elder_123", channel="phone")
        assert session.channel == "phone"

    def test_pwa_channel(self):
        session = SessionCreate(elder_id="elder_123", channel="pwa")
        assert session.channel == "pwa"


class TestSessionResponse:
    def test_session_response(self):
        resp = SessionResponse(
            id="session_001",
            elder_id="elder_123",
            channel="phone",
            status="complete",
            started_at=datetime(2024, 1, 1, 14, 0, 0),
            duration=600,
            topics_covered=["childhood", "cooking"],
        )
        assert resp.status == "complete"
        assert resp.duration == 600


class TestMomentResponse:
    def test_moment(self):
        moment = MomentResponse(
            id="moment_001",
            title="Mother's Baklava",
            summary="Fatima remembers learning to make baklava with her mother",
            quote="She always said the secret was patience with the layers",
            visual_description="A warm kitchen with golden pastry layers",
            emotional_tone="nostalgic",
            order=1,
        )
        assert moment.title == "Mother's Baklava"
        assert moment.order == 1


class TestReelResponse:
    def test_reel_generating(self):
        reel = ReelResponse(
            id="reel_001",
            session_id="session_001",
            elder_id="elder_123",
            status="generating",
            created_at=datetime(2024, 1, 1),
        )
        assert reel.status == "generating"
        assert reel.video_url == ""

    def test_reel_ready(self):
        reel = ReelResponse(
            id="reel_001",
            session_id="session_001",
            elder_id="elder_123",
            status="ready",
            video_url="https://storage.googleapis.com/reels/reel_001.mp4",
            duration=45,
            created_at=datetime(2024, 1, 1),
        )
        assert reel.video_url != ""
        assert reel.duration == 45
