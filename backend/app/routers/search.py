"""Search endpoint — full-text search across moments with filtering."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query

from app.middleware.auth import require_any_role
from app.services import firestore_families

router = APIRouter()


@router.get("/{family_id}/elders/{elder_id}/search")
async def search_moments(
    family_id: str,
    elder_id: str,
    q: str = Query("", description="Search query"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    people: Optional[str] = Query(None, description="Comma-separated people names to filter by"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    channel: Optional[str] = Query(None, description="Channel filter: phone or pwa"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: dict = Depends(require_any_role),
):
    """Search moments across all sessions for an elder.

    Supports full-text search combined with structured filters.
    Returns matching moments with session context.
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    people_list = [p.strip() for p in people.split(",")] if people else None

    results = await firestore_families.search_moments(
        elder_id=elder_id,
        query_text=q,
        tags=tag_list,
        people=people_list,
        date_from=date_from,
        date_to=date_to,
        channel=channel,
        limit=limit,
        offset=offset,
    )

    return {"results": results, "count": len(results), "query": q}
