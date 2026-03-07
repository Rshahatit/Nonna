"""Twilio Voice webhook endpoints."""

import logging
from fastapi import APIRouter, Form, Request, Response

from app.config import get_settings
from app.services import firestore
from app.services.twilio_service import build_media_stream_twiml, build_rejection_twiml

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/voice")
async def handle_inbound_call(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    CallSid: str = Form(...),
):
    """Handle inbound voice calls from Twilio. Looks up elder by phone number."""
    settings = get_settings()
    logger.info(f"Inbound call: from={From}, to={To}, sid={CallSid}")

    # Look up elder by phone number
    elder = await firestore.get_elder_by_phone(From)

    if not elder:
        logger.info(f"Unknown caller: {From}")
        return Response(content=build_rejection_twiml(), media_type="application/xml")

    # Create a new session for this call
    session = await firestore.create_session(elder.id, channel="phone")
    logger.info(f"Session created for inbound call: elder={elder.id}, session={session.id}")

    twiml = build_media_stream_twiml(session.id, settings.backend_url)
    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def handle_call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str = Form(default="0"),
):
    """Handle Twilio call status callbacks."""
    logger.info(f"Call status update: sid={CallSid}, status={CallStatus}, duration={CallDuration}")
    return {"status": "received"}
