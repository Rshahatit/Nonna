"""WebSocket endpoint for Twilio Media Streams (phone channel)."""

import asyncio
import base64
import json
import logging
import audioop
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.conversation import ConversationSession, register_session, unregister_session
from app.services.memory_extraction import extract_and_update_memory
from app.services.reel_pipeline import trigger_reel_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/phone-stream")
async def phone_stream(websocket: WebSocket):
    """Handle Twilio Media Stream WebSocket for phone conversations."""
    await websocket.accept()

    session: Optional[ConversationSession] = None
    session_id: Optional[str] = None
    stream_sid: Optional[str] = None

    async def forward_gemini_audio():
        """Forward Gemini audio responses back to Twilio."""
        if not session:
            return
        try:
            async for audio_chunk in session.receive_audio():
                # Convert PCM 16-bit 24kHz to mulaw 8kHz for Twilio
                # First downsample from 24kHz to 8kHz
                downsampled = audioop.ratecv(audio_chunk, 2, 1, 24000, 8000, None)[0]
                # Convert to mulaw
                mulaw_audio = audioop.lin2ulaw(downsampled, 2)

                payload = base64.b64encode(mulaw_audio).decode("utf-8")
                media_message = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": payload},
                }
                await websocket.send_json(media_message)
        except Exception as e:
            logger.error(f"Error forwarding Gemini audio: {e}")

    audio_task: Optional[asyncio.Task] = None

    try:
        async for raw_message in websocket.iter_text():
            message = json.loads(raw_message)
            event = message.get("event")

            if event == "start":
                # Extract session ID from stream parameters
                start_data = message.get("start", {})
                stream_sid = start_data.get("streamSid")
                custom_params = start_data.get("customParameters", {})
                session_id = custom_params.get("session_id")

                if not session_id:
                    logger.error("No session_id in stream parameters")
                    break

                # Look up the session to get elder_id
                from app.services.firestore import get_session
                session_data = await get_session(session_id)
                if not session_data:
                    logger.error(f"Session {session_id} not found")
                    break

                # Create and start conversation session
                session = ConversationSession(
                    elder_id=session_data.elder_id,
                    session_id=session_id,
                    channel="phone",
                )
                register_session(session)
                await session.start()

                # Start forwarding Gemini audio in background
                audio_task = asyncio.create_task(forward_gemini_audio())
                logger.info(f"Phone stream started: session={session_id}")

            elif event == "media" and session:
                # Decode Twilio mulaw audio and forward to Gemini
                payload = message["media"]["payload"]
                mulaw_data = base64.b64decode(payload)

                # Convert mulaw 8kHz to PCM 16-bit 16kHz for Gemini
                pcm_data = audioop.ulaw2lin(mulaw_data, 2)
                upsampled = audioop.ratecv(pcm_data, 2, 1, 8000, 16000, None)[0]

                await session.send_audio(upsampled)

            elif event == "stop":
                logger.info(f"Phone stream stopped: session={session_id}")
                break

    except WebSocketDisconnect:
        logger.info(f"Phone WebSocket disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"Phone stream error: {e}")
    finally:
        if audio_task:
            audio_task.cancel()
        if session:
            transcript = await session.end()
            unregister_session(session.session_id)

            # Trigger post-session pipeline
            if transcript.strip():
                asyncio.create_task(
                    _post_session_pipeline(session.session_id, session.elder_id, transcript)
                )


async def _post_session_pipeline(session_id: str, elder_id: str, transcript: str):
    """Run memory extraction, tagging, threading, and reel generation."""
    try:
        await extract_and_update_memory(session_id, elder_id, transcript)
        await trigger_reel_pipeline(session_id, elder_id)

        # Phase 2: auto-tagging and thread generation
        try:
            from app.services.tagging import tag_session_moments, generate_threads
            await tag_session_moments(session_id)
            from app.services.firestore import get_db
            db = get_db()
            elder_doc = await db.collection("elders").document(elder_id).get()
            if elder_doc.exists:
                family_id = elder_doc.to_dict().get("familyId")
                if family_id:
                    await generate_threads(family_id, elder_id)
        except Exception as e:
            logger.warning(f"Tagging/threading failed (non-fatal): {e}")

    except Exception as e:
        logger.error(f"Post-session pipeline failed: session={session_id}, error={e}")
        await firestore.update_session_status(session_id, status="failed")
