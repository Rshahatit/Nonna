"""Shared test configuration."""

import os

# Set dummy env vars before any imports that need them
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest123")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+15551234567")
