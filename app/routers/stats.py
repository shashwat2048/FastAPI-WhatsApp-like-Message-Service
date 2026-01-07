"""
Stats router.
"""
from fastapi import APIRouter
from app.storage import compute_stats

router = APIRouter()

@router.get("")
async def get_stats():
    """Get statistics about messages."""
    stats = compute_stats()
    return stats

