"""Tests for configuration module."""

import os
import pytest
from app.config import Settings


class TestSettings:
    def test_default_settings(self):
        """Settings should load with defaults for optional fields."""
        settings = Settings(
            gemini_api_key="test-key",
            twilio_account_sid="AC1234567890",
            twilio_auth_token="test-token",
            twilio_phone_number="+15551234567",
        )
        assert settings.gemini_api_key == "test-key"
        assert settings.google_cloud_project == ""
        assert settings.gcs_bucket_media == "nonna-media"
        assert settings.gcs_bucket_reels == "nonna-reels"
        assert settings.gcs_bucket_transcripts == "nonna-transcripts"
        assert settings.backend_url == "http://localhost:8000"
        assert settings.next_public_app_url == "http://localhost:3000"

    def test_custom_settings(self):
        settings = Settings(
            gemini_api_key="key",
            twilio_account_sid="AC123",
            twilio_auth_token="token",
            twilio_phone_number="+1555",
            google_cloud_project="my-project",
            backend_url="https://api.nonna.ai",
        )
        assert settings.google_cloud_project == "my-project"
        assert settings.backend_url == "https://api.nonna.ai"
