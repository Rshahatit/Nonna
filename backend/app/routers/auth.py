"""Authentication endpoints — user sign-in, profile, family lookup."""

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.user import UserResponse, FamilyResponse
from app.services import firestore_families

router = APIRouter()


@router.post("/signin", response_model=UserResponse)
async def sign_in(user: dict = Depends(get_current_user)):
    """Called after Firebase Auth sign-in to create/update user record."""
    return await firestore_families.upsert_user(
        uid=user["uid"],
        email=user["email"],
        name=user["name"],
        photo_url=user.get("picture", ""),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get the current user's profile."""
    db_user = await firestore_families.get_user(user["uid"])
    if not db_user:
        # Auto-create on first access
        return await firestore_families.upsert_user(
            uid=user["uid"],
            email=user["email"],
            name=user["name"],
            photo_url=user.get("picture", ""),
        )
    return db_user


@router.get("/me/families", response_model=list[FamilyResponse])
async def get_my_families(user: dict = Depends(get_current_user)):
    """List families the current user belongs to."""
    return await firestore_families.list_user_families(user["uid"])
