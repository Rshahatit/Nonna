"""Memory Reel generation pipeline: story extraction → images → narration → video assembly."""

import asyncio
import json
import logging
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from google.cloud import texttospeech_v1 as tts

from app.config import get_settings
from app.services import firestore
from app.services.storage import upload_image, upload_audio, upload_reel

logger = logging.getLogger(__name__)

# ──────────────────────────── Story Extraction ────────────────────────────

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


async def extract_story_moments(session_id: str, transcript: str, vision_context: list[str] = None) -> list[dict]:
    """Extract structured story moments from a session transcript."""
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    additional_context = ""
    if vision_context:
        additional_context = f"\n\nVISUAL CONTEXT FROM CAMERA (use to enrich scene descriptions):\n" + \
                           "\n".join(f"- {obs}" for obs in vision_context)

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
        moments = data.get("moments", [])
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse story extraction: {e}")
        return []

    # Save moments to Firestore
    for i, moment in enumerate(moments):
        moment["order"] = i
        await firestore.create_moment(session_id, {
            "title": moment["title"],
            "summary": moment["summary"],
            "quote": moment["quote"],
            "visual_description": moment["visual_description"],
            "emotional_tone": moment["emotional_tone"],
            "image_url": "",
            "order": i,
        })

    return moments


# ──────────────────────────── Image Generation ────────────────────────────

STYLE_PREFIX = (
    "Warm watercolor illustration in the style of a cherished memory, "
    "soft golden lighting, gentle and nostalgic mood, painterly brushstrokes, "
    "rich but muted colors. "
)


async def generate_moment_image(session_id: str, moment_id: str, visual_description: str) -> Optional[bytes]:
    """Generate an illustration for a story moment using Imagen 3."""
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
            gcs_url = await upload_image(session_id, moment_id, image_data)
            return image_data
        return None

    except Exception as e:
        logger.error(f"Image generation failed for moment {moment_id}: {e}")
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

        # Concatenate all segments with crossfade
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
    """Run the full reel generation pipeline for a completed session."""
    try:
        # Get elder info
        elder = await firestore.get_elder(elder_id)
        if not elder:
            logger.error(f"Elder {elder_id} not found for reel pipeline")
            return

        # Create reel record
        reel = await firestore.create_reel(session_id, elder_id)

        # Get session and transcript
        session = await firestore.get_session(session_id)

        # Get transcript from storage (for now, re-read from the session's processing)
        # In production this would read from GCS
        # For the pipeline, we pass transcript through the chain
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

        # Get vision context if available
        conversation_session = None
        vision_context = []

        # Step 1: Extract story moments
        logger.info(f"Reel pipeline: extracting moments for session {session_id}")
        moments = await extract_story_moments(session_id, transcript, vision_context)

        if not moments:
            logger.warning(f"No moments extracted for session {session_id}")
            await firestore.update_reel(reel.id, status="failed")
            return

        # Step 2: Generate images and narration in parallel
        logger.info(f"Reel pipeline: generating {len(moments)} images and narrations")

        # Get moment IDs from Firestore
        saved_moments = await firestore.list_moments(session_id)
        moment_ids = [m.id for m in saved_moments]

        # Generate images concurrently
        image_tasks = [
            generate_moment_image(session_id, mid, m["visual_description"])
            for mid, m in zip(moment_ids, moments)
        ]

        # Generate narrations concurrently
        narration_tasks = [
            generate_narration(session_id, mid, m["summary"])
            for mid, m in zip(moment_ids, moments)
        ]

        # Run images and narrations in parallel
        images, narrations = await asyncio.gather(
            asyncio.gather(*image_tasks),
            asyncio.gather(*narration_tasks),
        )

        # Step 3: Assemble video
        logger.info(f"Reel pipeline: assembling video for session {session_id}")
        video_data = await assemble_reel(
            session_id, elder.name, moments, list(images), list(narrations)
        )

        if video_data:
            gcs_url = f"gs://{settings.gcs_bucket_reels}/reels/{session_id}.mp4"
            await firestore.update_reel(
                reel.id,
                status="ready",
                videoUrl=gcs_url,
                duration=len(moments) * 10,  # approximate
            )
            await firestore.update_session_status(session_id, status="complete")
            logger.info(f"Reel pipeline complete: session={session_id}, reel={reel.id}")
        else:
            await firestore.update_reel(reel.id, status="failed")
            await firestore.update_session_status(session_id, status="failed")

    except Exception as e:
        logger.error(f"Reel pipeline error: session={session_id}, error={e}")
        try:
            await firestore.update_session_status(session_id, status="failed")
        except Exception:
            pass
