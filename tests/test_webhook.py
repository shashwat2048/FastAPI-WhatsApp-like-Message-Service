"""
Tests for webhook endpoint:
- Valid message insert
- Duplicate message handling
- HMAC signature validation
"""
import pytest
import hmac
import hashlib
import json
import tempfile
import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models import init_schema


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Set up test database and settings before each test."""
    # Create temporary database
    test_db_path = os.path.join(tempfile.gettempdir(), f'test_webhook_{os.getpid()}.db')
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)
    
    # Set environment variables
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db_path}")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret-key")
    
    # Patch settings in both config module and webhook router module
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{test_db_path}")
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", "test-secret-key")
    
    # Also patch in webhook router module
    import app.routers.webhook
    monkeypatch.setattr(app.routers.webhook.settings, "WEBHOOK_SECRET", "test-secret-key")
    
    # Initialize schema
    init_schema()
    
    yield
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_valid_webhook_insert(client):
    """Test valid message insertion via webhook."""
    payload = {
        "message_id": "msg-001",
        "from_msisdn": "+1234567890",
        "to_msisdn": "+0987654321",
        "ts": "2024-01-01T10:00:00Z",
        "text": "Test message"
    }
    
    # Generate HMAC signature - need to match what webhook receives
    # TestClient sends JSON, but webhook reads raw body bytes
    body_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        "test-secret-key".encode('utf-8'),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Use content parameter to send raw bytes to match signature
    response = client.post(
        "/webhook",
        content=body_bytes,
        headers={
            "X-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code != 200:
        print(f"Response: {response.status_code} - {response.json()}")
        from app.routers.webhook import settings as webhook_settings
        print(f"WEBHOOK_SECRET in webhook: {webhook_settings.WEBHOOK_SECRET}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    assert response.json()["status"] == "ok"


def test_duplicate_message(client):
    """Test that duplicate messages return 200 but are idempotent."""
    payload = {
        "message_id": "msg-duplicate",
        "from_msisdn": "+1234567890",
        "to_msisdn": "+0987654321",
        "ts": "2024-01-01T10:00:00Z",
        "text": "First message"
    }
    
    # Generate HMAC signature
    body_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        "test-secret-key".encode('utf-8'),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # First insert
    response1 = client.post(
        "/webhook",
        content=body_bytes,
        headers={
            "X-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    assert response1.status_code == 200
    
    # Duplicate insert (same message_id) - regenerate signature for same body
    body_bytes2 = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature2 = hmac.new(
        "test-secret-key".encode('utf-8'),
        body_bytes2,
        hashlib.sha256
    ).hexdigest()
    
    response2 = client.post(
        "/webhook",
        content=body_bytes2,
        headers={
            "X-Signature": signature2,
            "Content-Type": "application/json"
        }
    )
    # Should still return 200 (idempotent)
    assert response2.status_code == 200
    assert response2.json()["status"] == "ok"


def test_invalid_signature(client):
    """Test that invalid HMAC signatures are rejected."""
    payload = {
        "message_id": "msg-invalid",
        "from_msisdn": "+1234567890",
        "to_msisdn": "+0987654321",
        "ts": "2024-01-01T10:00:00Z",
        "text": "Test message"
    }
    
    invalid_signature = "invalid-signature-12345"
    
    response = client.post(
        "/webhook",
        json=payload,
        headers={"X-Signature": invalid_signature}
    )
    
    assert response.status_code == 401
    assert "invalid signature" in str(response.json()).lower()


def test_missing_signature(client):
    """Test that missing signatures are rejected."""
    payload = {
        "message_id": "msg-no-sig",
        "from_msisdn": "+1234567890",
        "to_msisdn": "+0987654321",
        "ts": "2024-01-01T10:00:00Z",
        "text": "Test message"
    }
    
    response = client.post(
        "/webhook",
        json=payload
        # No X-Signature header
    )
    
    assert response.status_code == 401
    assert "invalid signature" in str(response.json()).lower()

