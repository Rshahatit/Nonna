"""Firebase Authentication middleware and role-based access control."""

import logging
from typing import Optional, Literal
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

_firebase_app = None


def _get_firebase_app():
    """Lazily initialize Firebase Admin SDK."""
    global _firebase_app
    if _firebase_app is None:
        try:
            import firebase_admin
            from firebase_admin import credentials

            settings = get_settings()
            if settings.google_application_credentials:
                cred = credentials.Certificate(settings.google_application_credentials)
                _firebase_app = firebase_admin.initialize_app(cred)
            else:
                _firebase_app = firebase_admin.initialize_app()
        except ValueError:
            # Already initialized
            import firebase_admin
            _firebase_app = firebase_admin.get_app()
    return _firebase_app


async def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims."""
    try:
        from firebase_admin import auth as firebase_auth
        _get_firebase_app()
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Extract and verify the current user from the Authorization header.

    Returns a dict with uid, email, name, picture from Firebase token claims.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    decoded = await verify_firebase_token(credentials.credentials)
    return {
        "uid": decoded["uid"],
        "email": decoded.get("email", ""),
        "name": decoded.get("name", ""),
        "picture": decoded.get("picture", ""),
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Like get_current_user but returns None for unauthenticated requests."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


class RequireRole:
    """Dependency that checks the user's role within a family.

    Usage:
        @router.get("/families/{family_id}/settings")
        async def settings(
            family_id: str,
            auth: dict = Depends(RequireRole("organizer"))
        ):
    """

    def __init__(self, *allowed_roles: str):
        self.allowed_roles = set(allowed_roles) if allowed_roles else {"organizer", "member", "viewer"}

    async def __call__(
        self,
        request: Request,
        user: dict = Depends(get_current_user),
    ) -> dict:
        family_id = request.path_params.get("family_id")
        if not family_id:
            raise HTTPException(status_code=400, detail="family_id required in path")

        from app.services import firestore_families
        member = await firestore_families.get_family_member(family_id, user["uid"])

        if not member:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this family"
            )

        if member.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of these roles: {', '.join(self.allowed_roles)}"
            )

        return {**user, "role": member.role, "family_id": family_id}


# Convenience instances
require_organizer = RequireRole("organizer")
require_member_or_above = RequireRole("organizer", "member")
require_any_role = RequireRole("organizer", "member", "viewer")
