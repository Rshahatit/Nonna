"""Family notification service via Twilio SMS."""

import logging
from app.config import get_settings
from app.services import firestore
from app.services.twilio_service import get_twilio_client

logger = logging.getLogger(__name__)


async def notify_reel_ready(elder_id: str, session_id: str) -> None:
    """Send SMS notification to family member when a Memory Reel is ready."""
    settings = get_settings()
    elder = await firestore.get_elder(elder_id)
    if not elder or not elder.created_by:
        return

    # Only send if created_by looks like a phone number
    family_contact = elder.created_by
    if not family_contact.startswith("+"):
        return

    archive_url = f"{settings.next_public_app_url}/archive/{elder_id}"
    message = (
        f"A new Memory Reel from {elder.name} is ready! "
        f"Watch it here: {archive_url}"
    )

    try:
        client = get_twilio_client()
        client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=family_contact,
        )
        logger.info(f"Reel notification sent to {family_contact} for elder {elder_id}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


async def notify_missed_calls(elder_id: str) -> None:
    """Notify family member when elder misses consecutive scheduled calls."""
    settings = get_settings()
    elder = await firestore.get_elder(elder_id)
    if not elder or not elder.created_by:
        return

    family_contact = elder.created_by
    if not family_contact.startswith("+"):
        return

    message = (
        f"Hi — Nonna hasn't been able to reach {elder.name} for the last couple of scheduled calls. "
        f"Everything is probably fine, but you might want to check in."
    )

    try:
        client = get_twilio_client()
        client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=family_contact,
        )
        logger.info(f"Missed call notification sent for elder {elder_id}")
    except Exception as e:
        logger.error(f"Failed to send missed call notification: {e}")
