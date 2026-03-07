"""Tests for Nonna system prompt generation."""

import pytest
from app.prompts.nonna import (
    build_first_conversation_prompt,
    build_returning_conversation_prompt,
    BASE_PERSONALITY,
)
from app.models.elder import ElderMemory, PersonMentioned, PlaceMentioned


class TestFirstConversationPrompt:
    def test_includes_elder_name_and_seed(self):
        prompt = build_first_conversation_prompt(
            elder_name="Fatima",
            seed_context="Mom grew up in Amman, amazing cook",
            channel="phone",
        )
        assert "Fatima" in prompt
        assert "Amman" in prompt
        assert "amazing cook" in prompt

    def test_first_conversation_marker(self):
        prompt = build_first_conversation_prompt(
            elder_name="Fatima",
            seed_context="Test",
            channel="phone",
        )
        assert "First" in prompt

    def test_phone_channel_no_vision(self):
        prompt = build_first_conversation_prompt(
            elder_name="Fatima",
            seed_context="Test",
            channel="phone",
        )
        assert "Phone Call" in prompt
        assert "Camera" not in prompt

    def test_pwa_channel_includes_vision(self):
        prompt = build_first_conversation_prompt(
            elder_name="Fatima",
            seed_context="Test",
            channel="pwa",
        )
        assert "Camera" in prompt or "camera" in prompt


class TestReturningConversationPrompt:
    def test_includes_memory_context(self):
        memory = ElderMemory(
            people=[
                PersonMentioned(name="Samir", relationship="brother", first_mentioned="s1", details=["Lives in Amman"]),
            ],
            places=[
                PlaceMentioned(name="Amman", significance="Hometown", stories=["Old market"]),
            ],
            themes=["family bonds", "cooking"],
            session_count=3,
            conversation_style="loves tangents",
        )
        prompt = build_returning_conversation_prompt(
            elder_name="Fatima",
            seed_context="Mom grew up in Amman",
            memory=memory,
            channel="phone",
        )
        assert "Samir" in prompt
        assert "brother" in prompt
        assert "Amman" in prompt
        assert "3" in prompt
        assert "tangent" in prompt.lower()

    def test_empty_memory_still_valid(self):
        memory = ElderMemory()
        prompt = build_returning_conversation_prompt(
            elder_name="Fatima",
            seed_context="Test",
            memory=memory,
            channel="phone",
        )
        assert "Fatima" in prompt
        assert len(prompt) > 100

    def test_pwa_channel_has_vision(self):
        memory = ElderMemory(session_count=2)
        prompt = build_returning_conversation_prompt(
            elder_name="Fatima",
            seed_context="Test",
            memory=memory,
            channel="pwa",
        )
        assert "Camera" in prompt or "camera" in prompt


class TestBasePersonality:
    def test_personality_has_warmth(self):
        assert "warm" in BASE_PERSONALITY.lower()

    def test_personality_has_curiosity(self):
        assert "curious" in BASE_PERSONALITY.lower()

    def test_no_ai_self_reference(self):
        lower = BASE_PERSONALITY.lower()
        assert "as an ai" not in lower
        assert "i am a language model" not in lower

    def test_anti_patterns_listed(self):
        assert "NEVER" in BASE_PERSONALITY
