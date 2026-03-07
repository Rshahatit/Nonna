"""Twilio Voice integration for inbound and outbound calls."""

import logging
from typing import Optional

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect

from app.config import get_settings
from app.services import firestore

logger = logging.getLogger(__name__)

_twilio_client: Optional[Client] = None


def get_twilio_client() -> Client:
    global _twilio_client
    if _twilio_client is None:
        settings = get_settings()
        _twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    return _twilio_client


def build_media_stream_twiml(session_id: str, backend_url: str) -> str:
    """Build TwiML response that connects the call to a WebSocket media stream."""
    response = VoiceResponse()
    response.say("Connecting you to Nonna.", voice="Polly.Joanna")
    response.pause(length=1)

    connect = Connect()
    ws_url = backend_url.replace("https://", "wss://").replace("http://", "ws://")
    stream = connect.stream(url=f"{ws_url}/ws/phone-stream")
    stream.parameter(name="session_id", value=session_id)
    response.append(connect)

    return str(response)


def build_rejection_twiml() -> str:
    """Build TwiML for unrecognized callers."""
    response = VoiceResponse()
    response.say(
        "I'm sorry, I don't recognize this number. "
        "Please ask your family member to set up Nonna for you.",
        voice="Polly.Joanna",
    )
    response.hangup()
    return str(response)


async def place_outbound_call(elder_id: str) -> Optional[str]:
    """Place an outbound call to an elder."""
    settings = get_settings()
    elder = await firestore.get_elder(elder_id)
    if not elder:
        logger.error(f"Elder {elder_id} not found for outbound call")
        return None

    # Create a session for the call
    session = await firestore.create_session(elder_id, channel="phone")

    client = get_twilio_client()
    twiml = build_media_stream_twiml(session.id, settings.backend_url)

    try:
        call = client.calls.create(
            twiml=twiml,
            to=elder.phone_number,
            from_=settings.twilio_phone_number,
            status_callback=f"{settings.backend_url}/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )
        logger.info(f"Outbound call placed: call_sid={call.sid}, elder={elder_id}, session={session.id}")
        return call.sid
    except Exception as e:
        logger.error(f"Failed to place outbound call to elder {elder_id}: {e}")
        await firestore.update_session_status(session.id, status="failed")
        return None
