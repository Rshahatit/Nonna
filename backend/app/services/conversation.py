"""Gemini Live API conversation engine for real-time bidirectional audio."""

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.elder import ElderMemory
from app.models.navigator import SessionMode, NavigationContext
from app.prompts.nonna import build_first_conversation_prompt, build_returning_conversation_prompt
from app.prompts.navigator import build_navigator_prompt
from app.prompts.check_in import build_check_in_prompt
from app.prompts.assist import build_assist_prompt
from app.services import firestore
from app.services.navigation_tracker import NavigationTracker

logger = logging.getLogger(__name__)


class ConversationSession:
    """Manages a single live conversation session with an elder via Gemini Live API."""

    def __init__(self, elder_id: str, session_id: str, channel: str,
                 mode: SessionMode = "story"):
        self.elder_id = elder_id
        self.session_id = session_id
        self.channel = channel
        self.mode = mode
        self.transcript_lines: list[str] = []
        self.vision_observations: list[str] = []
        self._gemini_session = None
        self._client = None
        self._active = False
        self.nav_tracker: Optional[NavigationTracker] = None
        if mode in ("navigator", "assist"):
            self.nav_tracker = NavigationTracker(session_id)

    async def start(self) -> None:
        """Initialize the Gemini Live API session with elder context."""
        settings = get_settings()

        # Load elder data and memory
        elder = await firestore.get_elder(self.elder_id)
        if not elder:
            raise ValueError(f"Elder {self.elder_id} not found")

        memory = await firestore.get_elder_memory(self.elder_id)

        # Build appropriate system prompt based on mode
        system_prompt = self._build_prompt(elder, memory)

        # Initialize Gemini client
        self._client = genai.Client(api_key=settings.gemini_api_key)

        # Configure the Live API session
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=system_prompt)]
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            ),
        )

        self._gemini_session = await self._client.aio.live.connect(
            model=settings.gemini_live_model,
            config=config,
        )
        self._active = True
        logger.info(f"Conversation started: elder={self.elder_id}, session={self.session_id}, channel={self.channel}")

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm;rate=16000") -> None:
        """Send audio chunk from the elder to Gemini."""
        if not self._active or not self._gemini_session:
            return

        await self._gemini_session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=audio_data, mime_type=mime_type)
                ]
            )
        )

    def _build_prompt(self, elder, memory: ElderMemory) -> str:
        """Build the system prompt based on the current session mode."""
        if self.mode == "navigator":
            return build_navigator_prompt(elder_name=elder.name)
        elif self.mode == "check_in":
            return build_check_in_prompt(
                elder_name=elder.name,
                seed_context=elder.seed_context,
                memory=memory,
                channel=self.channel,
            )
        elif self.mode == "assist":
            return build_assist_prompt(
                elder_name=elder.name,
                has_screen=(self.channel == "pwa"),
            )
        else:
            # Story mode (default) — existing behavior
            if memory.session_count == 0:
                return build_first_conversation_prompt(
                    elder_name=elder.name,
                    seed_context=elder.seed_context,
                    channel=self.channel,
                )
            else:
                return build_returning_conversation_prompt(
                    elder_name=elder.name,
                    seed_context=elder.seed_context,
                    memory=memory,
                    channel=self.channel,
                )

    async def send_screenshot(self, screenshot_base64: str) -> None:
        """Send a screenshot to the Gemini Live session for navigator/assist mode analysis."""
        if not self._active or not self._gemini_session:
            return
        if self.mode not in ("navigator", "assist"):
            return

        frame_bytes = base64.b64decode(screenshot_base64)
        await self._gemini_session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=frame_bytes, mime_type="image/jpeg")
                ]
            )
        )

    async def send_vision_frame(self, frame_base64: str) -> None:
        """Send a camera frame for vision analysis (PWA channel only)."""
        if not self._active or not self._gemini_session or self.channel != "pwa":
            return

        frame_bytes = base64.b64decode(frame_base64)
        await self._gemini_session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=frame_bytes, mime_type="image/jpeg")
                ]
            )
        )

    async def receive_audio(self):
        """Async generator that yields audio response chunks from Gemini."""
        if not self._active or not self._gemini_session:
            return

        try:
            async for response in self._gemini_session.receive():
                if not self._active:
                    break

                server_content = response.server_content
                if server_content and server_content.model_turn:
                    for part in server_content.model_turn.parts:
                        if part.inline_data:
                            yield part.inline_data.data

                # Check if turn is complete
                if server_content and server_content.turn_complete:
                    continue

        except Exception as e:
            logger.error(f"Error receiving from Gemini: {e}")
            raise

    async def end(self) -> str:
        """End the conversation session and return the accumulated transcript."""
        self._active = False

        if self._gemini_session:
            try:
                await self._gemini_session.close()
            except Exception as e:
                logger.warning(f"Error closing Gemini session: {e}")

        # Update session in Firestore
        now = datetime.now(timezone.utc)
        session = await firestore.get_session(self.session_id)
        duration = int((now - session.started_at).total_seconds()) if session else 0

        await firestore.update_session_status(
            self.session_id,
            status="processing",
            endedAt=now,
            duration=duration,
        )

        transcript = "\n".join(self.transcript_lines)
        logger.info(f"Conversation ended: session={self.session_id}, duration={duration}s")
        return transcript

    def add_transcript_line(self, speaker: str, text: str) -> None:
        """Add a line to the transcript."""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.transcript_lines.append(f"[{timestamp}] {speaker}: {text}")

    def add_vision_observation(self, observation: str) -> None:
        """Record a vision observation for reel generation."""
        self.vision_observations.append(observation)


# Active sessions registry
_active_sessions: dict[str, ConversationSession] = {}


def get_active_session(session_id: str) -> Optional[ConversationSession]:
    return _active_sessions.get(session_id)


def register_session(session: ConversationSession) -> None:
    _active_sessions[session.session_id] = session


def unregister_session(session_id: str) -> None:
    _active_sessions.pop(session_id, None)
