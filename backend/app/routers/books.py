"""Keepsake book endpoints — generate, preview, and manage books."""

import asyncio
from fastapi import APIRouter, HTTPException, Depends

from app.middleware.auth import require_member_or_above, require_any_role
from app.models.user import BookCreate, BookResponse
from app.services import firestore_families
from app.services.book_generator import generate_book_pdf

router = APIRouter()


@router.post("/{family_id}/books", response_model=BookResponse, status_code=201)
async def create_book(family_id: str, data: BookCreate,
                      auth: dict = Depends(require_member_or_above)):
    """Create a new keepsake book and start generation."""
    book = await firestore_families.create_book(family_id, auth["uid"], data)

    # Start PDF generation in background
    asyncio.create_task(generate_book_pdf(book.id))

    return book


@router.get("/{family_id}/books", response_model=list[BookResponse])
async def list_books(family_id: str, auth: dict = Depends(require_any_role)):
    """List all books for a family."""
    return await firestore_families.list_books(family_id)


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: str):
    """Get book details including PDF URL and status."""
    book = await firestore_families.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
