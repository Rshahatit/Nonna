"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Google Cloud
    google_cloud_project: str = ""
    google_application_credentials: str = ""

    # Firestore
    firestore_database: str = "(default)"

    # Google Cloud Storage
    gcs_bucket_transcripts: str = "nonna-transcripts"
    gcs_bucket_media: str = "nonna-media"
    gcs_bucket_reels: str = "nonna-reels"

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    gemini_live_model: str = "gemini-2.5-flash-exp"
    gemini_image_model: str = "gemini-2.5-flash-preview-04-17"

    # Vertex AI
    vertex_ai_location: str = "us-central1"

    # Google Cloud TTS
    tts_voice_name: str = "en-US-Journey-F"
    tts_speaking_rate: float = 0.9

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Backend
    backend_url: str = "http://localhost:8000"
    backend_port: int = 8000

    # Frontend
    next_public_backend_url: str = "http://localhost:8000"
    next_public_app_url: str = "http://localhost:3000"

    # Cloud Tasks
    cloud_tasks_queue: str = "nonna-reel-pipeline"
    cloud_tasks_location: str = "us-central1"

    # Firebase Auth (Phase 2)
    firebase_project_id: str = ""

    # SendGrid (Phase 2 — email notifications)
    sendgrid_api_key: str = ""

    # Local development
    use_local_storage: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
