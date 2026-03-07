"""WebSocket endpoint for PWA sessions (audio + vision channel)."""

import asyncio
import base64
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.conversation import ConversationSession, register_session, unregister_session
from app.services.memory_extraction import extract_and_update_memory
from app.services.reel_pipeline import trigger_reel_pipeline
from app.services import firestore

logger = logging.getLogger(__name__)
router = APIRouter()

# Throttle vision observations to max 1 per 30 seconds
VISION_THROTTLE_SECONDS = 30


@router.websocket("/ws/pwa-stream")
async def pwa_stream(websocket: WebSocket):
    """Handle PWA WebSocket for audio + vision conversations."""
    await websocket.accept()

    session: Optional[ConversationSession] = None
    last_vision_time: float = 0

    async def forward_gemini_audio():
        """Forward Gemini audio responses to the PWA client."""
        if not session:
            return
        try:
            async for audio_chunk in session.receive_audio():
                # Send PCM audio to browser for playback
                payload = base64.b64encode(audio_chunk).decode("utf-8")
                await websocket.send_json({
                    "type": "audio",
                    "data": payload,
                })
        except Exception as e:
            logger.error(f"Error forwarding Gemini audio to PWA: {e}")

    audio_task: Optional[asyncio.Task] = None

    try:
        async for raw_message in websocket.iter_text():
            message = json.loads(raw_message)
            msg_type = message.get("type")

            if msg_type == "start":
                elder_id = message.get("elder_id")
                if not elder_id:
                    await websocket.send_json({"type": "error", "message": "elder_id required"})
                    break

                # Create session
                session_data = await firestore.create_session(elder_id, channel="pwa")

                session = ConversationSession(
                    elder_id=elder_id,
                    session_id=session_data.id,
                    channel="pwa",
                )
                register_session(session)
                await session.start()

                audio_task = asyncio.create_task(forward_gemini_audio())

                await websocket.send_json({
                    "type": "started",
                    "session_id": session_data.id,
                })
                logger.info(f"PWA stream started: elder={elder_id}, session={session_data.id}")

            elif msg_type == "audio" and session:
                # Decode and forward audio to Gemini
                audio_data = base64.b64decode(message["data"])
                await session.send_audio(audio_data)

            elif msg_type == "frame" and session:
                # Camera frame — throttle and forward to Gemini vision
                now = time.time()
                if now - last_vision_time >= VISION_THROTTLE_SECONDS:
                    last_vision_time = now
                    frame_data = message.get("data", "")
                    if frame_data:
                        await session.send_vision_frame(frame_data)

            elif msg_type == "stop":
                logger.info(f"PWA stream stop requested: session={session.session_id if session else 'none'}")
                break

    except WebSocketDisconnect:
        logger.info(f"PWA WebSocket disconnected: session={session.session_id if session else 'none'}")
    except Exception as e:
        logger.error(f"PWA stream error: {e}")
    finally:
        if audio_task:
            audio_task.cancel()
        if session:
            transcript = await session.end()
            unregister_session(session.session_id)

            if transcript.strip():
                asyncio.create_task(
                    _post_session_pipeline(session.session_id, session.elder_id, transcript)
                )


async def _post_session_pipeline(session_id: str, elder_id: str, transcript: str):
    """Run memory extraction and reel generation after session ends."""
    try:
        await extract_and_update_memory(session_id, elder_id, transcript)
        await trigger_reel_pipeline(session_id, elder_id)
    except Exception as e:
        logger.error(f"Post-session pipeline failed: session={session_id}, error={e}")
        await firestore.update_session_status(session_id, status="failed")
