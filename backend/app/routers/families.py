"""Family management endpoints — CRUD, members, invites, elders."""

from fastapi import APIRouter, HTTPException, Depends

from app.middleware.auth import (
    get_current_user, require_organizer, require_member_or_above, require_any_role,
)
from app.models.user import (
    FamilyCreate, FamilyResponse, FamilyMemberResponse, FamilyMemberUpdate,
    InviteCreate, InviteResponse,
)
from app.services import firestore_families

router = APIRouter()


# ──────────────────────────── Family CRUD ────────────────────────────

@router.post("", response_model=FamilyResponse, status_code=201)
async def create_family(data: FamilyCreate, user: dict = Depends(get_current_user)):
    """Create a new family group."""
    return await firestore_families.create_family(
        name=data.name, created_by=user["uid"],
    )


@router.get("/{family_id}", response_model=FamilyResponse)
async def get_family(family_id: str, auth: dict = Depends(require_any_role)):
    """Get family details."""
    family = await firestore_families.get_family(family_id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


@router.put("/{family_id}", response_model=dict)
async def update_family(family_id: str, data: FamilyCreate,
                        auth: dict = Depends(require_organizer)):
    """Update family name (organizer only)."""
    success = await firestore_families.update_family(family_id, data.name)
    if not success:
        raise HTTPException(status_code=404, detail="Family not found")
    return {"status": "updated"}


# ──────────────────────────── Elders ────────────────────────────

@router.post("/{family_id}/elders", response_model=dict)
async def link_elder(family_id: str, elder_id: str,
                     auth: dict = Depends(require_organizer)):
    """Link an elder to this family (organizer only)."""
    await firestore_families.add_elder_to_family(family_id, elder_id)
    return {"status": "linked"}


# ──────────────────────────── Members ────────────────────────────

@router.get("/{family_id}/members", response_model=list[FamilyMemberResponse])
async def list_members(family_id: str, auth: dict = Depends(require_any_role)):
    """List all family members."""
    return await firestore_families.list_family_members(family_id)


@router.put("/{family_id}/members/{user_id}", response_model=dict)
async def update_member(family_id: str, user_id: str,
                        data: FamilyMemberUpdate,
                        auth: dict = Depends(require_organizer)):
    """Update a member's role or notification prefs (organizer only)."""
    success = await firestore_families.update_family_member(family_id, user_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "updated"}


@router.put("/{family_id}/members/{user_id}/prefs", response_model=dict)
async def update_own_prefs(family_id: str, user_id: str,
                           data: FamilyMemberUpdate,
                           user: dict = Depends(get_current_user)):
    """Update own notification preferences (any member)."""
    # Only allow updating own prefs
    if user["uid"] != user_id:
        # Check if organizer
        member = await firestore_families.get_family_member(family_id, user["uid"])
        if not member or member.role != "organizer":
            raise HTTPException(status_code=403, detail="Can only update your own preferences")

    # Only allow prefs update, not role
    prefs_only = FamilyMemberUpdate(notification_prefs=data.notification_prefs)
    success = await firestore_families.update_family_member(family_id, user_id, prefs_only)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "updated"}


@router.delete("/{family_id}/members/{user_id}", response_model=dict)
async def remove_member(family_id: str, user_id: str,
                        auth: dict = Depends(require_organizer)):
    """Remove a family member (organizer only)."""
    if auth["uid"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    success = await firestore_families.remove_family_member(family_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "removed"}


# ──────────────────────────── Invites ────────────────────────────

@router.post("/{family_id}/invites", response_model=InviteResponse, status_code=201)
async def create_invite(family_id: str, data: InviteCreate,
                        auth: dict = Depends(require_organizer)):
    """Generate an invite to the family (organizer only)."""
    return await firestore_families.create_invite(family_id, auth["uid"], data)


@router.get("/{family_id}/invites", response_model=list[InviteResponse])
async def list_invites(family_id: str, auth: dict = Depends(require_organizer)):
    """List pending invites (organizer only)."""
    return await firestore_families.list_family_invites(family_id)


@router.delete("/{family_id}/invites/{invite_id}", response_model=dict)
async def revoke_invite(family_id: str, invite_id: str,
                        auth: dict = Depends(require_organizer)):
    """Revoke a pending invite (organizer only)."""
    success = await firestore_families.revoke_invite(invite_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invite not found or already used")
    return {"status": "revoked"}
