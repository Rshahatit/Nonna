"""Tests for Twilio TwiML generation."""

import pytest
from app.services.twilio_service import build_media_stream_twiml, build_rejection_twiml


class TestTwiMLGeneration:
    def test_media_stream_twiml(self):
        """Should produce valid TwiML with WebSocket stream."""
        twiml = build_media_stream_twiml("session_123", "https://api.nonna.ai")
        assert "<Response>" in twiml
        assert "<Connect>" in twiml
        assert "<Stream" in twiml
        assert "wss://api.nonna.ai/ws/phone-stream" in twiml
        assert "session_123" in twiml

    def test_media_stream_twiml_http_to_ws(self):
        """Should convert http to ws protocol."""
        twiml = build_media_stream_twiml("s1", "http://localhost:8000")
        assert "ws://localhost:8000/ws/phone-stream" in twiml

    def test_rejection_twiml(self):
        """Should produce rejection message with hangup."""
        twiml = build_rejection_twiml()
        assert "<Response>" in twiml
        assert "<Say" in twiml
        assert "<Hangup" in twiml
        assert "don't recognize" in twiml.lower() or "recognize" in twiml.lower()
