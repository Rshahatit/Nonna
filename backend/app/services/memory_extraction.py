"""Post-session memory extraction using Gemini to update elder's persistent memory."""

import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.elder import ElderMemory, PersonMentioned, PlaceMentioned, LifeEvent, RecipeOrSkill
from app.services import firestore
from app.services.storage import upload_transcript

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are analyzing a conversation transcript between Nonna (an AI companion) and an elder. Extract structured memory data that will help Nonna remember this elder in future conversations.

Given the transcript and the elder's existing memory context, extract:

1. **new_people**: People mentioned for the first time (not already in existing memory). Include name, relationship to the elder, and key details.
2. **new_places**: Places mentioned for the first time. Include name and significance.
3. **new_life_events**: Life events mentioned for the first time. Include event description, approximate date if mentioned, and details.
4. **new_themes**: Emotional or topical themes that emerged (e.g., "resilience", "family bonds", "nostalgia for homeland").
5. **new_recipes_and_skills**: Any recipes, cooking techniques, crafts, or skills mentioned.
6. **updated_people**: Existing people with NEW details learned in this session.
7. **story_gaps**: Topics or life areas that haven't been explored yet and would be natural to ask about in future conversations.
8. **conversation_style_notes**: Observations about how this elder likes to converse (e.g., "loves tangents", "needs gentle prompting", "gets emotional about family", "very detail-oriented").
9. **topics_covered**: Brief list of topics discussed in this session.

Respond with valid JSON only, matching this structure:
{
  "new_people": [{"name": "", "relationship": "", "details": [""]}],
  "new_places": [{"name": "", "significance": ""}],
  "new_life_events": [{"event": "", "approximate_date": "", "details": ""}],
  "new_themes": [""],
  "new_recipes_and_skills": [{"name": "", "description": ""}],
  "updated_people": [{"name": "", "new_details": [""]}],
  "story_gaps": [""],
  "conversation_style_notes": "",
  "topics_covered": [""]
}
"""


async def extract_and_update_memory(session_id: str, elder_id: str, transcript: str) -> None:
    """Extract memory from transcript and merge with elder's existing memory."""
    settings = get_settings()

    # Save transcript to Cloud Storage
    transcript_url = await upload_transcript(session_id, transcript)
    await firestore.update_session_status(session_id, status="processing", transcriptUrl=transcript_url)

    # Load existing memory
    existing_memory = await firestore.get_elder_memory(elder_id)

    # Build context for extraction
    existing_context = f"""
Existing people known: {json.dumps([p.model_dump() for p in existing_memory.people], default=str)}
Existing places known: {json.dumps([p.model_dump() for p in existing_memory.places], default=str)}
Existing themes: {existing_memory.themes}
Previous session count: {existing_memory.session_count}
"""

    # Call Gemini for extraction
    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Content(parts=[types.Part(text=EXTRACTION_PROMPT)]),
            types.Content(parts=[types.Part(text=f"EXISTING MEMORY CONTEXT:\n{existing_context}")]),
            types.Content(parts=[types.Part(text=f"TRANSCRIPT:\n{transcript}")]),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    try:
        extracted = json.loads(response.text)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse memory extraction response: {e}")
        return

    # Merge extracted data with existing memory
    merged = _merge_memory(existing_memory, extracted, session_id)

    # Update topics covered on session
    topics = extracted.get("topics_covered", [])
    new_people_names = [p["name"] for p in extracted.get("new_people", [])]
    await firestore.update_session_status(
        session_id,
        status="processing",
        topicsCovered=topics,
        newPeopleMentioned=new_people_names,
    )

    # Save updated memory
    await firestore.update_elder_memory(elder_id, merged)
    logger.info(f"Memory updated for elder {elder_id} from session {session_id}")


def _merge_memory(existing: ElderMemory, extracted: dict, session_id: str) -> ElderMemory:
    """Merge newly extracted data into existing memory without overwriting."""
    from datetime import datetime, timezone

    # Add new people
    existing_names = {p.name.lower() for p in existing.people}
    for p in extracted.get("new_people", []):
        if p["name"].lower() not in existing_names:
            existing.people.append(PersonMentioned(
                name=p["name"],
                relationship=p.get("relationship", ""),
                first_mentioned=session_id,
                details=p.get("details", []),
            ))

    # Update existing people with new details
    for update in extracted.get("updated_people", []):
        for person in existing.people:
            if person.name.lower() == update["name"].lower():
                person.details.extend(update.get("new_details", []))

    # Add new places
    existing_place_names = {p.name.lower() for p in existing.places}
    for p in extracted.get("new_places", []):
        if p["name"].lower() not in existing_place_names:
            existing.places.append(PlaceMentioned(
                name=p["name"],
                significance=p.get("significance", ""),
            ))

    # Add new life events
    for e in extracted.get("new_life_events", []):
        existing.life_events.append(LifeEvent(
            event=e["event"],
            approximate_date=e.get("approximate_date", ""),
            details=e.get("details", ""),
        ))

    # Merge themes (deduplicate)
    existing_themes_lower = {t.lower() for t in existing.themes}
    for t in extracted.get("new_themes", []):
        if t.lower() not in existing_themes_lower:
            existing.themes.append(t)

    # Add recipes and skills
    for s in extracted.get("new_recipes_and_skills", []):
        existing.recipes_and_skills.append(RecipeOrSkill(
            name=s["name"],
            description=s.get("description", ""),
            session_id=session_id,
        ))

    # Update story gaps (replace with fresh analysis)
    existing.story_gaps = extracted.get("story_gaps", existing.story_gaps)

    # Update conversation style
    style_note = extracted.get("conversation_style_notes", "")
    if style_note:
        if existing.conversation_style:
            existing.conversation_style += f" | {style_note}"
        else:
            existing.conversation_style = style_note

    # Update session count and date
    existing.session_count += 1
    existing.last_session_date = datetime.now(timezone.utc)

    return existing
