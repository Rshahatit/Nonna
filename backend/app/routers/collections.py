"""Collection endpoints — curate themed groups of moments."""

from fastapi import APIRouter, HTTPException, Depends

from app.middleware.auth import require_member_or_above, require_organizer, require_any_role
from app.models.user import (
    CollectionCreate, CollectionResponse, CollectionUpdate, MomentRef,
)
from app.services import firestore_families

router = APIRouter()


@router.post("/{family_id}/collections", response_model=CollectionResponse, status_code=201)
async def create_collection(family_id: str, data: CollectionCreate,
                            auth: dict = Depends(require_member_or_above)):
    """Create a new collection (member or organizer)."""
    return await firestore_families.create_collection(family_id, auth["uid"], data)


@router.get("/{family_id}/collections", response_model=list[CollectionResponse])
async def list_collections(family_id: str, auth: dict = Depends(require_any_role)):
    """List all collections for a family."""
    return await firestore_families.list_collections(family_id)


@router.get("/{family_id}/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(family_id: str, collection_id: str,
                         auth: dict = Depends(require_any_role)):
    """Get a collection's details with all moment refs."""
    coll = await firestore_families.get_collection(collection_id)
    if not coll or coll.family_id != family_id:
        raise HTTPException(status_code=404, detail="Collection not found")
    return coll


@router.put("/{family_id}/collections/{collection_id}", response_model=dict)
async def update_collection(family_id: str, collection_id: str,
                            data: CollectionUpdate,
                            auth: dict = Depends(require_member_or_above)):
    """Update collection name, description, or public status."""
    coll = await firestore_families.get_collection(collection_id)
    if not coll or coll.family_id != family_id:
        raise HTTPException(status_code=404, detail="Collection not found")
    await firestore_families.update_collection(collection_id, data)
    return {"status": "updated"}


@router.delete("/{family_id}/collections/{collection_id}", response_model=dict)
async def delete_collection(family_id: str, collection_id: str,
                            auth: dict = Depends(require_organizer)):
    """Delete a collection (organizer only)."""
    success = await firestore_families.delete_collection(collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"status": "deleted"}


@router.post("/{family_id}/collections/{collection_id}/moments", response_model=dict)
async def add_moment(family_id: str, collection_id: str, ref: MomentRef,
                     auth: dict = Depends(require_member_or_above)):
    """Add a moment to a collection."""
    coll = await firestore_families.get_collection(collection_id)
    if not coll or coll.family_id != family_id:
        raise HTTPException(status_code=404, detail="Collection not found")
    await firestore_families.add_moment_to_collection(collection_id, ref)
    return {"status": "added"}


@router.delete("/{family_id}/collections/{collection_id}/moments", response_model=dict)
async def remove_moment(family_id: str, collection_id: str, ref: MomentRef,
                        auth: dict = Depends(require_member_or_above)):
    """Remove a moment from a collection."""
    await firestore_families.remove_moment_from_collection(collection_id, ref)
    return {"status": "removed"}
