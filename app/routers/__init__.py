"""
API routers.
"""
from fastapi import APIRouter
from app.metrics import get_metrics
from fastapi.responses import PlainTextResponse, JSONResponse
from app.storage import list_messages, compute_stats
from app.models import init_db
from typing import Optional

# Webhook router (placeholder - will be implemented later)
webhook_router = APIRouter()

@webhook_router.post("")
async def webhook():
    """Webhook endpoint for receiving messages."""
    return {"status": "not implemented yet"}


# Messages router
messages_router = APIRouter()

@messages_router.get("")
async def get_messages(
    from_msisdn: Optional[str] = None,
    since: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Get paginated and filtered messages."""
    filters = {}
    if from_msisdn:
        filters["from_msisdn"] = from_msisdn
    if since:
        filters["since"] = since
    if q:
        filters["q"] = q
    
    rows, total = list_messages(filters=filters, limit=limit, offset=offset)
    return {
        "messages": rows,
        "total": total,
        "limit": limit,
        "offset": offset
    }


# Stats router
stats_router = APIRouter()

@stats_router.get("")
async def get_stats():
    """Get statistics about messages."""
    stats = compute_stats()
    return stats


# Health router
health_router = APIRouter()

@health_router.get("/live")
async def liveness():
    """Liveness probe endpoint."""
    return {"status": "alive"}

@health_router.get("/ready")
async def readiness():
    """Readiness probe endpoint."""
    # Check database connection
    try:
        conn = init_db()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": str(e)}
        )


# Metrics router
metrics_router = APIRouter()

@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus-style metrics endpoint."""
    return get_metrics()

