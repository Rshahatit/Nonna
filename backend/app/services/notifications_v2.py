"""Enhanced notification system with per-member preferences and multi-channel delivery."""

import logging
from app.config import get_settings
from app.services import firestore_families
from app.services.twilio_service import get_twilio_client

logger = logging.getLogger(__name__)


async def notify_family_reel_ready(family_id: str, elder_id: str, session_id: str) -> int:
    """Send reel-ready notifications to all family members with that preference enabled.

    Returns the number of notifications sent.
    """
    settings = get_settings()
    members = await firestore_families.list_family_members(family_id)
    elder = None

    # Get elder name
    from app.services.firestore import get_elder
    elder = await get_elder(elder_id)
    elder_name = elder.name if elder else "your elder"

    archive_url = f"{settings.next_public_app_url}/family/{family_id}/archive/{elder_id}"
    sent = 0

    for member in members:
        prefs = member.notification_prefs
        if not prefs.reel_ready:
            continue

        message = (
            f"A new Memory Reel from {elder_name} is ready! "
            f"Watch it here: {archive_url}"
        )

        # SMS
        if prefs.channel in ("sms", "both"):
            # Look up user's phone if available (would need phone on user profile)
            # For now, skip SMS for family members without phone
            pass

        # Email
        if prefs.channel in ("email", "both") and member.email:
            await _send_email(
                to=member.email,
                subject=f"New Memory Reel from {elder_name}",
                body=message,
            )
            sent += 1

    return sent


async def notify_missed_calls_family(family_id: str, elder_id: str) -> int:
    """Notify organizers when elder misses consecutive scheduled calls."""
    settings = get_settings()
    members = await firestore_families.list_family_members(family_id)

    from app.services.firestore import get_elder
    elder = await get_elder(elder_id)
    elder_name = elder.name if elder else "your elder"

    sent = 0
    for member in members:
        if member.role != "organizer":
            continue
        if not member.notification_prefs.missed_calls:
            continue

        message = (
            f"Hi - Nonna hasn't been able to reach {elder_name} for the last "
            f"couple of scheduled calls. Everything is probably fine, but you "
            f"might want to check in."
        )

        if member.email:
            await _send_email(
                to=member.email,
                subject=f"Missed calls with {elder_name}",
                body=message,
            )
            sent += 1

    return sent


async def send_weekly_digest(family_id: str, elder_id: str) -> int:
    """Send weekly digest email to members who opted in."""
    settings = get_settings()
    members = await firestore_families.list_family_members(family_id)

    from app.services.firestore import get_elder, list_sessions
    elder = await get_elder(elder_id)
    elder_name = elder.name if elder else "your elder"

    # Count recent sessions (last 7 days)
    from datetime import datetime, timezone, timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_sessions = await list_sessions(elder_id=elder_id, limit=100)
    new_count = sum(1 for s in recent_sessions if s.started_at >= week_ago)

    if new_count == 0:
        return 0

    archive_url = f"{settings.next_public_app_url}/family/{family_id}/archive/{elder_id}"
    sent = 0

    for member in members:
        if not member.notification_prefs.weekly_digest:
            continue
        if not member.email:
            continue

        message = (
            f"This week with {elder_name}: {new_count} new conversation"
            f"{'s' if new_count != 1 else ''}. "
            f"Visit the archive to see the latest stories: {archive_url}"
        )

        await _send_email(
            to=member.email,
            subject=f"Weekly update: {elder_name}'s stories",
            body=message,
        )
        sent += 1

    return sent


async def _send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via SendGrid or fall back to logging."""
    settings = get_settings()

    if hasattr(settings, "sendgrid_api_key") and settings.sendgrid_api_key:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail

            sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
            message = Mail(
                from_email="nonna@nonna.ai",
                to_emails=to,
                subject=subject,
                plain_text_content=body,
            )
            sg.send(message)
            logger.info(f"Email sent to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"SendGrid email failed: {e}")
            return False
    else:
        logger.info(f"Email (not sent, no SendGrid key): to={to}, subject={subject}")
        return False
