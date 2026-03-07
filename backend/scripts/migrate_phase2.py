"""Phase 2 migration script: wraps existing Phase 1 elders in family groups,
backfills moment tags, and generates threads.

Usage:
    python -m scripts.migrate_phase2

Idempotent — safe to run multiple times.
"""

import asyncio
import logging
import sys

sys.path.insert(0, ".")

from app.services.firestore import get_db
from app.services.firestore_families import migrate_elder_to_family
from app.services.tagging import tag_session_moments, generate_threads

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    db = get_db()

    # Step 1: Migrate elders to family groups
    logger.info("=== Step 1: Migrating elders to family groups ===")
    elder_count = 0
    async for doc in db.collection("elders").stream():
        elder_id = doc.id
        d = doc.to_dict()

        if d.get("familyId"):
            logger.info(f"  Elder {elder_id} ({d['name']}) already migrated, skipping")
            continue

        family = await migrate_elder_to_family(elder_id)
        if family:
            logger.info(f"  Migrated elder {elder_id} ({d['name']}) -> family {family.id} ({family.name})")
            elder_count += 1

    logger.info(f"  Migrated {elder_count} elders")

    # Step 2: Backfill moment tags
    logger.info("=== Step 2: Backfilling moment tags ===")
    session_count = 0
    async for doc in db.collection("sessions").stream():
        session_id = doc.id
        d = doc.to_dict()

        if d.get("status") not in ("complete", "processing"):
            continue

        # Check if already tagged (check first moment)
        moments_query = db.collection("sessions").document(session_id).collection("moments").limit(1)
        has_tags = False
        async for mdoc in moments_query.stream():
            m = mdoc.to_dict()
            if m.get("tags"):
                has_tags = True

        if has_tags:
            logger.info(f"  Session {session_id} already tagged, skipping")
            continue

        try:
            await tag_session_moments(session_id)
            session_count += 1
            logger.info(f"  Tagged session {session_id}")
        except Exception as e:
            logger.error(f"  Failed to tag session {session_id}: {e}")

    logger.info(f"  Tagged {session_count} sessions")

    # Step 3: Generate threads
    logger.info("=== Step 3: Generating threads ===")
    async for doc in db.collection("elders").stream():
        elder_id = doc.id
        d = doc.to_dict()
        family_id = d.get("familyId")

        if not family_id:
            continue

        try:
            count = await generate_threads(family_id, elder_id)
            logger.info(f"  Generated {count} threads for elder {elder_id}")
        except Exception as e:
            logger.error(f"  Failed to generate threads for elder {elder_id}: {e}")

    logger.info("=== Migration complete ===")


if __name__ == "__main__":
    asyncio.run(main())
