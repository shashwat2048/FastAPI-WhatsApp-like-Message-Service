"""
Structured JSON logging utilities.
"""
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON (one object per line)."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
        }
        
        # Add request fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        
        # Add webhook-specific fields if present
        if hasattr(record, "message_id"):
            log_data["message_id"] = record.message_id
        if hasattr(record, "dup"):
            log_data["dup"] = record.dup
        if hasattr(record, "result"):
            log_data["result"] = record.result
        
        # Add message if present
        if record.getMessage():
            log_data["message"] = record.getMessage()
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Ensure valid JSON (one object per line)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up structured JSON logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests as structured JSON."""
    
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log structured JSON."""
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
            
            # Log request
            self.logger.info(
                "",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "latency_ms": latency_ms,
                }
            )
        
        return response


def log_webhook_event(
    logger: logging.Logger,
    request_id: str,
    message_id: str,
    dup: bool,
    result: str
):
    """
    Log webhook-specific event with structured JSON.
    
    Args:
        logger: Logger instance
        request_id: Request ID from request state
        message_id: Message ID from webhook payload
        dup: Whether message is duplicate
        result: Result of webhook processing ("created" or "duplicate")
    """
    logger.info(
        "webhook_event",
        extra={
            "request_id": request_id,
            "message_id": message_id,
            "dup": dup,
            "result": result,
        }
    )

