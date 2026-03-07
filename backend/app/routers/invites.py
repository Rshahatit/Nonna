"""Public invite endpoints — viewable without auth, redeemable with auth."""

from fastapi import APIRouter, HTTPException, Depends

from app.middleware.auth import get_current_user
from app.models.user import InviteResponse, FamilyMemberResponse
from app.services import firestore_families

router = APIRouter()


@router.get("/{token}", response_model=InviteResponse)
async def get_invite(token: str):
    """Get invite details by token (no auth required).

    Returns family name, inviter name, and role so the invite landing page
    can display context before the user signs in.
    """
    invite = await firestore_families.get_invite_by_token(token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    return invite


@router.post("/{token}/redeem", response_model=FamilyMemberResponse)
async def redeem_invite(token: str, user: dict = Depends(get_current_user)):
    """Redeem an invite token (requires auth).

    The authenticated user joins the family with the role specified in the invite.
    """
    member = await firestore_families.redeem_invite(token, user["uid"])
    if not member:
        raise HTTPException(
            status_code=400,
            detail="Invite is invalid, expired, or already redeemed"
        )
    return member
