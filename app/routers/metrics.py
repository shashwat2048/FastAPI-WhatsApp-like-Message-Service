"""
Metrics router.
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from app.metrics import get_metrics

router = APIRouter()

@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus-style metrics endpoint."""
    return get_metrics()

