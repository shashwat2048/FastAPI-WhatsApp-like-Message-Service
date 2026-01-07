"""
Messages router.
"""
from fastapi import APIRouter, Query
from app.storage import list_messages
from typing import Optional

router = APIRouter()

@router.get("")
async def get_messages(
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    from_msisdn: Optional[str] = Query(None, alias="from", description="Filter by sender MSISDN"),
    since: Optional[str] = Query(None, description="Filter messages since ISO-8601 timestamp"),
    q: Optional[str] = Query(None, description="Case-insensitive substring search on message text")
):
    """
    Get paginated and filtered messages.
    
    Returns messages ordered by ts ASC, message_id ASC.
    Total count ignores limit/offset.
    """
    filters = {}
    if from_msisdn:
        filters["from_msisdn"] = from_msisdn
    if since:
        filters["since"] = since
    if q:
        filters["q"] = q
    
    rows, total = list_messages(filters=filters, limit=limit, offset=offset)
    return {
        "data": rows,
        "total": total,
        "limit": limit,
        "offset": offset
    }

