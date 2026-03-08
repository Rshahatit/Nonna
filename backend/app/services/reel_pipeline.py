"""Memory Reel generation pipeline: story extraction + illustration → narration → video assembly.

Primary path: single Gemini interleaved text+image call (extracts moments AND generates illustrations).
Fallback: separate Gemini text extraction + Imagen 3 image generation.
"""

import asyncio
import json
import logging
import re
import subprocess
import tempfile
import os
from io import BytesIO
from typing import Optional

from google import genai
from google.genai import types
from google.genai.types import Modality
from google.cloud import texttospeech_v1 as tts
from PIL import Image

from app.config import get_settings
from app.services import firestore
from app.services.storage import upload_image, upload_audio, upload_reel

logger = logging.getLogger(__name__)

# ──────────────── Interleaved Story + Image Generation (Primary) ────────────────

INTERLEAVED_PROMPT_TEMPLATE = """You are creating a Memory Reel — a short illustrated story based on a conversation with {elder_name}.

Here is the conversation transcript:
{transcript}
{additional_context}
Create 3-5 story moments from this conversation. For each moment:
1. Write the moment metadata in EXACTLY this format:
MOMENT: [short evocative title, 3-7 words]
SUMMARY: [2-3 sentences in warm third person, e.g. "She remembered..." / "He described..."]
QUOTE: [the elder's exact words — the most powerful or touching sentence]
TONE: [one word: nostalgic, joyful, bittersweet, proud, tender, etc.]

2. Then generate a warm, painterly watercolor illustration of the scene described.

Style for ALL illustrations: Warm watercolor illustration in the style of a cherished memory, soft golden lighting, gentle and nostalgic mood, painterly brushstrokes, rich but muted colors. Include rich cultural and environmental details from the story. 16:9 landscape composition.

Order moments by narrative flow. Output each moment's text block followed immediately by its illustration image."""


def _build_interleaved_prompt(transcript: str, elder_name: str, vision_context: list[str] = None) -> str:
    additional_context = ""
    if vision_context:
        additional_context = (
            "\n\nVISUAL CONTEXT FROM CAMERA (use to enrich scene descriptions):\n"
            + "\n".join(f"- {obs}" for obs in vision_context)
            + "\n"
        )
    return INTERLEAVED_PROMPT_TEMPLATE.format(
        elder_name=elder_name,
        transcript=transcript,
        additional_context=additional_context,
    )


def _parse_moment_text(text: str) -> dict:
    """Parse a text block with MOMENT/SUMMARY/QUOTE/TONE labels."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("MOMENT:"):
            result["title"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("QUOTE:"):
            result["quote"] = line.split(":", 1)[1].strip().strip("\"'")
        elif line.upper().startswith("TONE:"):
            result["emotional_tone"] = line.split(":", 1)[1].strip()
    return result if "title" in result else {}


def _parse_interleaved_response(response) -> list[dict]:
    """Parse Gemini interleaved text+image response into structured moments."""
    moments = []
    current_moment = {}

    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            parsed = _parse_moment_text(part.text)
            if parsed:
                # If we already have a partial moment without an image, save it first
                if current_moment.get("title") and "image_data" not in current_moment:
                    moments.append(current_moment)
                current_moment = parsed
        elif hasattr(part, "inline_data") and part.inline_data:
            image = Image.open(BytesIO(part.inline_data.data))
            # Convert to PNG bytes
            buf = BytesIO()
            image.save(buf, format="PNG")
            current_moment["image_data"] = buf.getvalue()

            if "title" in current_moment:
                moments.append(current_moment)
                current_moment = {}

    # Handle trailing moment without image
    if current_moment.get("title"):
        moments.append(current_moment)

    return moments


async def generate_story_with_illustrations(
    session_id: str,
    transcript: str,
    elder_name: str,
    vision_context: list[str] = None,
) -> list[dict]:
    """Primary path: single Gemini call returning interleaved text + images."""
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = _build_interleaved_prompt(transcript, elder_name, vision_context)

    logger.info(f"Reel pipeline: using interleaved Gemini generation (model={settings.gemini_image_model})")

    response = await client.aio.models.generate_content(
        model=settings.gemini_image_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=[Modality.TEXT, Modality.IMAGE],
            temperature=0.4,
        ),
    )

    moments = _parse_interleaved_response(response)

    if not moments:
        raise ValueError("Interleaved response produced no parseable moments")

    # Ensure each moment has required fields with defaults
    for m in moments:
        m.setdefault("summary", m.get("title", ""))
        m.setdefault("quote", "")
        m.setdefault("emotional_tone", "nostalgic")
        m.setdefault("visual_description", "")  # Not needed for interleaved, but kept for schema

    logger.info(f"Interleaved generation produced {len(moments)} moments "
                f"({sum(1 for m in moments if 'image_data' in m)} with images)")
    return moments


# ──────────────── Fallback: Separate Extraction + Imagen 3 ────────────────

STORY_EXTRACTION_PROMPT = """You are extracting story moments from a conversation between Nonna (an AI companion) and an elder. These moments will become a Memory Reel — a short narrated video with illustrated scenes.

From the transcript, extract 2-5 of the most compelling story moments. Each moment should be a self-contained memory or insight that would resonate with the elder's family.

For each moment, provide:
1. **title**: A short, evocative title (3-7 words)
2. **summary**: A 2-3 sentence summary narrated in warm third person ("She remembered..." / "He described...")
3. **quote**: The elder's exact words (or close paraphrase) — the most powerful or touching sentence from this moment
4. **visual_description**: A detailed description of the scene to illustrate. Use warm, painterly imagery. Be specific about setting, colors, lighting, and mood. This will be used to generate an illustration.
5. **emotional_tone**: One word capturing the emotion (e.g., "nostalgic", "joyful", "bittersweet", "proud", "tender")

Order the moments by narrative flow (not necessarily chronological).

Respond with valid JSON:
{
  "moments": [
    {
      "title": "",
      "summary": "",
      "quote": "",
      "visual_description": "",
      "emotional_tone": ""
    }
  ]
}
"""

STYLE_PREFIX = (
    "Warm watercolor illustration in the style of a cherished memory, "
    "soft golden lighting, gentle and nostalgic mood, painterly brushstrokes, "
    "rich but muted colors. "
)


async def _extract_story_moments_text_only(
    transcript: str, vision_context: list[str] = None
) -> list[dict]:
    """Fallback: extract moments as structured JSON (no images)."""
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    additional_context = ""
    if vision_context:
        additional_context = (
            "\n\nVISUAL CONTEXT FROM CAMERA (use to enrich scene descriptions):\n"
            + "\n".join(f"- {obs}" for obs in vision_context)
        )

    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Content(parts=[types.Part(text=STORY_EXTRACTION_PROMPT)]),
            types.Content(parts=[types.Part(text=f"TRANSCRIPT:\n{transcript}{additional_context}")]),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )

    try:
        data = json.loads(response.text)
        return data.get("moments", [])
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse story extraction: {e}")
        return []


async def _generate_moment_image_imagen(
    session_id: str, moment_id: str, visual_description: str
) -> Optional[bytes]:
    """Fallback: generate illustration using Imagen 3 via Vertex AI."""
    settings = get_settings()

    try:
        from google.cloud import aiplatform
        from vertexai.preview.vision_models import ImageGenerationModel

        aiplatform.init(
            project=settings.google_cloud_project,
            location=settings.vertex_ai_location,
        )

        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        prompt = f"{STYLE_PREFIX}{visual_description}"

        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9",
        )

        if response.images:
            image_data = response.images[0]._image_bytes
            await upload_image(session_id, moment_id, image_data)
            return image_data
        return None

    except Exception as e:
        logger.error(f"Imagen 3 fallback failed for moment {moment_id}: {e}")
        return None


# ──────────────────────────── Narration (TTS) ────────────────────────────

async def generate_narration(session_id: str, moment_id: str, text: str) -> Optional[bytes]:
    """Generate voiceover narration using Google Cloud TTS."""
    settings = get_settings()

    try:
        client = tts.TextToSpeechAsyncClient()

        ssml = f"""<speak>
            <prosody rate="{settings.tts_speaking_rate}">
                {text}
            </prosody>
            <break time="800ms"/>
        </speak>"""

        synthesis_input = tts.SynthesisInput(ssml=ssml)
        voice = tts.VoiceSelectionParams(
            language_code="en-US",
            name=settings.tts_voice_name,
        )
        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
        )

        response = await client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        audio_data = response.audio_content
        await upload_audio(session_id, moment_id, audio_data)
        return audio_data

    except Exception as e:
        logger.error(f"TTS generation failed for moment {moment_id}: {e}")
        return None


# ──────────────────────────── Video Assembly (FFmpeg) ────────────────────────────

async def assemble_reel(session_id: str, elder_name: str,
                        moments: list[dict], images: list[bytes], narrations: list[bytes]) -> Optional[bytes]:
    """Assemble the final Memory Reel MP4 using FFmpeg."""
    with tempfile.TemporaryDirectory() as tmpdir:
        segment_files = []

        for i, (moment, image_data, audio_data) in enumerate(zip(moments, images, narrations)):
            if not image_data or not audio_data:
                continue

            img_path = os.path.join(tmpdir, f"moment_{i}.png")
            audio_path = os.path.join(tmpdir, f"moment_{i}.wav")
            segment_path = os.path.join(tmpdir, f"segment_{i}.mp4")

            # Write files
            with open(img_path, "wb") as f:
                f.write(image_data)
            with open(audio_path, "wb") as f:
                f.write(audio_data)

            # Get audio duration
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.stdout.strip() else 5.0

            # Create segment with Ken Burns effect (subtle zoom)
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-i", audio_path,
                "-filter_complex",
                f"[0:v]scale=1920:1080,zoompan=z='min(zoom+0.0005,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration * 25)}:s=1920x1080:fps=25[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-shortest",
                segment_path,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logger.error(f"FFmpeg segment {i} failed: {proc.stderr}")
                continue
            segment_files.append(segment_path)

        if not segment_files:
            logger.error(f"No segments created for session {session_id}")
            return None

        # Create concat file
        concat_path = os.path.join(tmpdir, "concat.txt")
        with open(concat_path, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        # Concatenate all segments
        output_path = os.path.join(tmpdir, "reel.mp4")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
        proc = subprocess.run(concat_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error(f"FFmpeg concat failed: {proc.stderr}")
            return None

        with open(output_path, "rb") as f:
            video_data = f.read()

        # Upload to Cloud Storage
        await upload_reel(session_id, video_data)
        return video_data


# ──────────────────────────── Pipeline Orchestration ────────────────────────────

async def trigger_reel_pipeline(session_id: str, elder_id: str) -> None:
    """Run the full reel generation pipeline for a completed session.

    Primary: Gemini interleaved text+image (single call for extraction + illustration).
    Fallback: Gemini text extraction + Imagen 3 image generation (separate calls).
    """
    try:
        # Get elder info
        elder = await firestore.get_elder(elder_id)
        if not elder:
            logger.error(f"Elder {elder_id} not found for reel pipeline")
            return

        # Create reel record
        reel = await firestore.create_reel(session_id, elder_id)

        # Get transcript from storage
        from app.services.storage import get_storage_client
        settings = get_settings()

        try:
            client = get_storage_client()
            bucket = client.bucket(settings.gcs_bucket_transcripts)
            blob = bucket.blob(f"transcripts/{session_id}.txt")
            transcript = blob.download_as_text()
        except Exception:
            logger.warning(f"Could not load transcript for {session_id}, using empty")
            transcript = ""

        if not transcript:
            await firestore.update_reel(reel.id, status="failed")
            return

        vision_context = []
        used_interleaved = False

        # ── Primary path: interleaved generation ──
        try:
            logger.info(f"Reel pipeline: attempting interleaved generation for session {session_id}")
            moments = await generate_story_with_illustrations(
                session_id, transcript, elder.name, vision_context
            )
            used_interleaved = True
        except Exception as e:
            logger.warning(f"Interleaved generation failed, falling back to Imagen 3: {e}")
            moments = None

        # ── Fallback path: separate extraction + Imagen 3 ──
        if not moments:
            logger.info(f"Reel pipeline: using fallback (text extraction + Imagen 3)")
            moments = await _extract_story_moments_text_only(transcript, vision_context)

        if not moments:
            logger.warning(f"No moments extracted for session {session_id}")
            await firestore.update_reel(reel.id, status="failed")
            return

        # Save moments to Firestore
        for i, moment in enumerate(moments):
            moment["order"] = i
            await firestore.create_moment(session_id, {
                "title": moment.get("title", ""),
                "summary": moment.get("summary", ""),
                "quote": moment.get("quote", ""),
                "visual_description": moment.get("visual_description", ""),
                "emotional_tone": moment.get("emotional_tone", "nostalgic"),
                "image_url": "",
                "order": i,
            })

        # Get moment IDs from Firestore
        saved_moments = await firestore.list_moments(session_id)
        moment_ids = [m.id for m in saved_moments]

        # ── Image handling ──
        if used_interleaved:
            # Images already generated — extract bytes and upload to storage
            images = []
            for mid, m in zip(moment_ids, moments):
                img_data = m.pop("image_data", None)
                if img_data:
                    await upload_image(session_id, mid, img_data)
                images.append(img_data)
        else:
            # Fallback: generate images separately with Imagen 3
            logger.info(f"Reel pipeline: generating {len(moments)} images via Imagen 3")
            image_tasks = [
                _generate_moment_image_imagen(session_id, mid, m.get("visual_description", ""))
                for mid, m in zip(moment_ids, moments)
            ]
            images = list(await asyncio.gather(*image_tasks))

        # ── Narration (always via TTS) ──
        logger.info(f"Reel pipeline: generating {len(moments)} narrations")
        narration_tasks = [
            generate_narration(session_id, mid, m.get("summary", ""))
            for mid, m in zip(moment_ids, moments)
        ]
        narrations = list(await asyncio.gather(*narration_tasks))

        # ── Video assembly ──
        logger.info(f"Reel pipeline: assembling video for session {session_id}")
        video_data = await assemble_reel(
            session_id, elder.name, moments, images, narrations
        )

        if video_data:
            gcs_url = f"gs://{settings.gcs_bucket_reels}/reels/{session_id}.mp4"
            await firestore.update_reel(
                reel.id,
                status="ready",
                videoUrl=gcs_url,
                duration=len(moments) * 10,
            )
            await firestore.update_session_status(session_id, status="complete")
            method = "interleaved" if used_interleaved else "fallback (Imagen 3)"
            logger.info(f"Reel pipeline complete: session={session_id}, reel={reel.id}, method={method}")
        else:
            await firestore.update_reel(reel.id, status="failed")
            await firestore.update_session_status(session_id, status="failed")

    except Exception as e:
        logger.error(f"Reel pipeline error: session={session_id}, error={e}")
        try:
            await firestore.update_session_status(session_id, status="failed")
        except Exception:
            pass
