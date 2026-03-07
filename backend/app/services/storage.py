"""Google Cloud Storage service for media files."""

from datetime import timedelta
from typing import Optional
from google.cloud import storage
from app.config import get_settings

_client: Optional[storage.Client] = None


def get_storage_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=get_settings().google_cloud_project)
    return _client


async def upload_file(bucket_name: str, blob_path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{bucket_name}/{blob_path}"


async def upload_transcript(session_id: str, transcript: str) -> str:
    settings = get_settings()
    return await upload_file(
        settings.gcs_bucket_transcripts,
        f"transcripts/{session_id}.txt",
        transcript.encode("utf-8"),
        "text/plain",
    )


async def upload_image(session_id: str, moment_id: str, image_data: bytes) -> str:
    settings = get_settings()
    return await upload_file(
        settings.gcs_bucket_media,
        f"images/{session_id}/{moment_id}.png",
        image_data,
        "image/png",
    )


async def upload_audio(session_id: str, moment_id: str, audio_data: bytes) -> str:
    settings = get_settings()
    return await upload_file(
        settings.gcs_bucket_media,
        f"audio/{session_id}/{moment_id}.wav",
        audio_data,
        "audio/wav",
    )


async def upload_reel(session_id: str, video_data: bytes) -> str:
    settings = get_settings()
    return await upload_file(
        settings.gcs_bucket_reels,
        f"reels/{session_id}.mp4",
        video_data,
        "video/mp4",
    )


def get_signed_url(bucket_name: str, blob_path: str, expiration_hours: int = 24) -> str:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=expiration_hours),
        method="GET",
    )
    return url
