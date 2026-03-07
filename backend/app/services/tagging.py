"""Post-session auto-tagging pipeline and cross-session thread generation."""

import json
import logging
from collections import defaultdict

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.user import MomentRef
from app.services.firestore import get_db
from app.services import firestore_families

logger = logging.getLogger(__name__)

TAG_TAXONOMY = [
    "recipe", "life_lesson", "family_history", "skill_craft",
    "tradition", "humor", "love_story", "hardship",
    "achievement", "daily_life",
]

TAGGING_PROMPT = f"""You are analyzing story moments from a conversation between Nonna (an AI companion) and an elder. For each moment, extract tags and entities.

Tag taxonomy (use only these tags): {', '.join(TAG_TAXONOMY)}

For each moment, return:
1. **tags**: One or more tags from the taxonomy above. If nothing fits well, use "daily_life".
2. **people_mentioned**: Names of people mentioned in this moment (just first names or how the elder refers to them).
3. **place_mentioned**: A single place name if one is prominently mentioned, or null.

Respond with valid JSON:
{{
  "moments": [
    {{
      "moment_id": "<the id you received>",
      "tags": ["tag1", "tag2"],
      "people_mentioned": ["Name1", "Name2"],
      "place_mentioned": "Place name or null"
    }}
  ]
}}
"""


async def tag_session_moments(session_id: str) -> list[dict]:
    """Auto-tag all moments in a session with categories, people, and places."""
    settings = get_settings()
    db = get_db()

    # Load moments
    moments = []
    query = db.collection("sessions").document(session_id).collection("moments").order_by("order")
    async for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        moments.append(d)

    if not moments:
        return []

    # Build input for Gemini
    moments_input = json.dumps([{
        "moment_id": m["id"],
        "title": m.get("title", ""),
        "summary": m.get("summary", ""),
        "quote": m.get("quote", ""),
    } for m in moments], indent=2)

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Content(parts=[types.Part(text=TAGGING_PROMPT)]),
            types.Content(parts=[types.Part(text=f"MOMENTS:\n{moments_input}")]),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    try:
        result = json.loads(response.text)
        tagged_moments = result.get("moments", [])
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse tagging response: {e}")
        return []

    # Update each moment with tags
    for tagged in tagged_moments:
        moment_id = tagged.get("moment_id")
        if not moment_id:
            continue

        # Validate tags against taxonomy
        valid_tags = [t for t in tagged.get("tags", []) if t in TAG_TAXONOMY]
        if not valid_tags:
            valid_tags = ["daily_life"]

        update = {
            "tags": valid_tags,
            "peopleMentioned": tagged.get("people_mentioned", []),
            "placeMentioned": tagged.get("place_mentioned"),
        }

        try:
            await db.collection("sessions").document(session_id).collection(
                "moments"
            ).document(moment_id).update(update)
        except Exception as e:
            logger.error(f"Failed to update moment {moment_id} tags: {e}")

    logger.info(f"Tagged {len(tagged_moments)} moments for session {session_id}")
    return tagged_moments


async def generate_threads(family_id: str, elder_id: str) -> int:
    """Generate cross-session threads from tagged moments.

    Creates person, place, and theme threads when entities appear across 2+ sessions.
    Returns the number of threads created/updated.
    """
    db = get_db()

    # Collect all moments across sessions for this elder
    sessions_query = db.collection("sessions").where("elderId", "==", elder_id)

    # Build maps: entity -> {session_ids, moment_refs}
    people_map: dict[str, dict] = defaultdict(lambda: {"sessions": set(), "refs": []})
    place_map: dict[str, dict] = defaultdict(lambda: {"sessions": set(), "refs": []})
    theme_map: dict[str, dict] = defaultdict(lambda: {"sessions": set(), "refs": []})

    async for session_doc in sessions_query.stream():
        sid = session_doc.id
        moments_query = db.collection("sessions").document(sid).collection("moments")

        async for moment_doc in moments_query.stream():
            m = moment_doc.to_dict()
            mid = moment_doc.id
            ref = MomentRef(session_id=sid, moment_id=mid)

            # People
            for person in m.get("peopleMentioned", []):
                person_key = person.strip()
                if person_key:
                    people_map[person_key]["sessions"].add(sid)
                    people_map[person_key]["refs"].append(ref)

            # Places
            place = m.get("placeMentioned")
            if place and place.strip():
                place_key = place.strip()
                place_map[place_key]["sessions"].add(sid)
                place_map[place_key]["refs"].append(ref)

            # Themes/tags
            for tag in m.get("tags", []):
                theme_map[tag]["sessions"].add(sid)
                theme_map[tag]["refs"].append(ref)

    thread_count = 0

    # Create person threads (2+ sessions)
    for person, data in people_map.items():
        if len(data["sessions"]) >= 2:
            await firestore_families.upsert_thread(
                family_id=family_id, elder_id=elder_id,
                thread_type="person", name=person,
                moment_refs=data["refs"],
                session_count=len(data["sessions"]),
            )
            thread_count += 1

    # Create place threads (2+ sessions)
    for place, data in place_map.items():
        if len(data["sessions"]) >= 2:
            friendly_name = f"Stories from {place}"
            await firestore_families.upsert_thread(
                family_id=family_id, elder_id=elder_id,
                thread_type="place", name=friendly_name,
                moment_refs=data["refs"],
                session_count=len(data["sessions"]),
            )
            thread_count += 1

    # Create theme threads (3+ sessions)
    theme_display = {
        "recipe": "Recipes & Cooking",
        "life_lesson": "Life Lessons",
        "family_history": "Family History",
        "skill_craft": "Skills & Crafts",
        "tradition": "Traditions",
        "humor": "Funny Stories",
        "love_story": "Love Stories",
        "hardship": "Overcoming Hardship",
        "achievement": "Achievements",
        "daily_life": "Daily Life",
    }
    for tag, data in theme_map.items():
        if len(data["sessions"]) >= 3:
            display_name = theme_display.get(tag, tag.replace("_", " ").title())
            await firestore_families.upsert_thread(
                family_id=family_id, elder_id=elder_id,
                thread_type="theme", name=display_name,
                moment_refs=data["refs"],
                session_count=len(data["sessions"]),
            )
            thread_count += 1

    logger.info(f"Generated {thread_count} threads for elder {elder_id}")
    return thread_count
