from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import time
import uuid
import logging
from app.config import settings
from app.models import init_schema
from app.logging_utils import setup_logging
from app.metrics import get_metrics, record_http_request, record_latency
from app import routers

# Setup logging
logger = setup_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    logger.info("Initializing database schema...")
    init_schema()
    logger.info("Database schema initialized")
    yield
    # Shutdown (if needed in the future)
    pass


# Create FastAPI app with lifespan
app = FastAPI(
    title="FastAPI Backend",
    description="A FastAPI backend application",
    version="1.0.0",
    lifespan=lifespan
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and record metrics."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request, log structured JSON, and record metrics."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calculate latency
            latency_ms = round((time.time() - start_time) * 1000, 2)
            
            # Log structured JSON
            logger.info(
                "",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "latency_ms": latency_ms,
                }
            )
            
            # Record metrics
            record_http_request(request.url.path, status_code)
            record_latency(latency_ms)
        
        return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware (after CORS)
app.add_middleware(RequestLoggingMiddleware)


# Include routers
app.include_router(routers.webhook_router, prefix="/webhook", tags=["webhook"])
app.include_router(routers.messages_router, prefix="/messages", tags=["messages"])
app.include_router(routers.stats_router, prefix="/stats", tags=["stats"])
app.include_router(routers.health_router, prefix="/health", tags=["health"])
app.include_router(routers.metrics_router, tags=["metrics"])


@app.get("/favicon.ico")
async def favicon():
    """Return 204 No Content for favicon requests."""
    return Response(status_code=204)

