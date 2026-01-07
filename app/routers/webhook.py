"""
Webhook router.
"""
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from app.config import settings
from app.storage import insert_message
from app.logging_utils import log_webhook_event
from app.metrics import record_webhook_request


router = APIRouter()


class WebhookPayload(BaseModel):
    """Webhook payload model."""
    message_id: str = Field(..., min_length=1)
    from_msisdn: str = Field(..., pattern=r'^\+?\d{1,15}$')  # E.164-like (more lenient)
    to_msisdn: str = Field(..., pattern=r'^\+?\d{1,15}$')  # E.164-like (more lenient)
    ts: str = Field(...)  # ISO-8601 UTC with Z
    text: Optional[str] = Field(None, max_length=4096)
    
    @field_validator('ts')
    @classmethod
    def validate_ts(cls, v: str) -> str:
        """Validate ISO-8601 UTC timestamp with Z."""
        try:
            # Parse ISO-8601 with Z suffix
            if not v.endswith('Z'):
                raise ValueError("Timestamp must end with 'Z' (UTC)")
            # Remove Z and parse
            dt = datetime.fromisoformat(v.rstrip('Z'))
            return v
        except ValueError as e:
            raise ValueError(f"Invalid ISO-8601 UTC timestamp: {e}")


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature.
    
    Args:
        body: Raw request body bytes
        signature: Signature from X-Signature header
        secret: Secret key for HMAC
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not secret:
        return False
    
    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


@router.post("")
async def webhook(request: Request):
    """
    Webhook endpoint for receiving messages.
    
    Validates HMAC signature, processes payload, and inserts message idempotently.
    """
    # Get request ID from middleware
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Read raw request body bytes
    body_bytes = await request.body()
    
    # Get signature from header
    signature = request.headers.get('X-Signature', '')
    
    # Validate signature
    if not settings.WEBHOOK_SECRET:
        record_webhook_request('validation_error')
        raise HTTPException(
            status_code=401,
            detail="invalid signature"
        )
    
    if not verify_signature(body_bytes, signature, settings.WEBHOOK_SECRET):
        record_webhook_request('invalid_signature')
        raise HTTPException(
            status_code=401,
            detail="invalid signature"
        )
    
    # Parse and validate payload
    try:
        import json
        payload_dict = json.loads(body_bytes.decode('utf-8'))
        payload = WebhookPayload(**payload_dict)
    except json.JSONDecodeError:
        record_webhook_request('validation_error')
        raise HTTPException(
            status_code=400,
            detail="invalid JSON"
        )
    except Exception as e:
        record_webhook_request('validation_error')
        raise HTTPException(
            status_code=400,
            detail=f"validation error: {str(e)}"
        )
    
    # Prepare message data for storage
    message_data = {
        "message_id": payload.message_id,
        "from_msisdn": payload.from_msisdn,
        "to_msisdn": payload.to_msisdn,
        "ts": payload.ts,
        "text": payload.text,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    # Insert message idempotently
    result = insert_message(message_data)
    
    # Determine if duplicate
    dup = (result == "duplicate")
    
    # Record metrics
    record_webhook_request(result)
    
    # Log webhook-specific fields
    from app.logging_utils import setup_logging
    logger = setup_logging(settings.LOG_LEVEL)
    log_webhook_event(
        logger=logger,
        request_id=request_id,
        message_id=payload.message_id,
        dup=dup,
        result=result
    )
    
    # Always return 200 on valid signature
    return {"status": "ok"}

