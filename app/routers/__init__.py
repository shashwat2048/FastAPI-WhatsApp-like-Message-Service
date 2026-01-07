"""
API routers.
"""
from app.routers.webhook import router as webhook_router
from app.routers.messages import router as messages_router
from app.routers.stats import router as stats_router
from app.routers.health import router as health_router
from app.routers.metrics import router as metrics_router

__all__ = [
    "webhook_router",
    "messages_router",
    "stats_router",
    "health_router",
    "metrics_router",
]

