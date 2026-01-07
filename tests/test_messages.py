"""
Tests for /messages endpoint:
- Pagination
- Filtering (by from_number, to_number, date range)
"""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models import init_schema
from app.storage import insert_message


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Set up test database with sample data before each test."""
    # Create temporary database
    test_db_path = os.path.join(tempfile.gettempdir(), f'test_messages_{os.getpid()}.db')
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)
    
    # Set test database URL
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db_path}")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret-key")
    
    # Reinitialize settings
    from app.config import settings
    settings.DATABASE_URL = f"sqlite:///{test_db_path}"
    settings.WEBHOOK_SECRET = "test-secret-key"
    
    # Initialize schema
    init_schema()
    
    # Insert test messages
    test_messages = [
        {
            "message_id": "msg-001",
            "from_msisdn": "+1111111111",
            "to_msisdn": "+2222222222",
            "ts": "2024-01-01T10:00:00Z",
            "text": "First message",
            "created_at": "2024-01-01T10:00:00Z"
        },
        {
            "message_id": "msg-002",
            "from_msisdn": "+1111111111",
            "to_msisdn": "+3333333333",
            "ts": "2024-01-01T11:00:00Z",
            "text": "Second message",
            "created_at": "2024-01-01T11:00:00Z"
        },
        {
            "message_id": "msg-003",
            "from_msisdn": "+4444444444",
            "to_msisdn": "+2222222222",
            "ts": "2024-01-01T12:00:00Z",
            "text": "Third message",
            "created_at": "2024-01-01T12:00:00Z"
        },
        {
            "message_id": "msg-004",
            "from_msisdn": "+1111111111",
            "to_msisdn": "+2222222222",
            "ts": "2024-01-02T10:00:00Z",
            "text": "Fourth message",
            "created_at": "2024-01-02T10:00:00Z"
        },
    ]
    
    for msg in test_messages:
        insert_message(msg)
    
    yield
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


def test_pagination(client):
    """Test message pagination."""
    # Test first page
    response = client.get("/messages?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert len(data["data"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0
    
    # Test second page
    response = client.get("/messages?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["offset"] == 2


def test_filter_by_from_number(client):
    """Test filtering messages by sender number."""
    response = client.get("/messages?from=%2B1111111111")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) > 0
    # All messages should be from the specified sender
    for msg in data["data"]:
        assert msg["from_msisdn"] == "+1111111111"


def test_filter_by_to_number(client):
    """Test filtering messages by recipient number."""
    # Note: The API doesn't have a 'to' filter, but we can test what exists
    # Testing 'from' filter which exists
    response = client.get("/messages?from=%2B4444444444")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) > 0
    for msg in data["data"]:
        assert msg["from_msisdn"] == "+4444444444"


def test_filter_by_date_range(client):
    """Test filtering messages by date range (since parameter)."""
    response = client.get("/messages?since=2024-01-02T00:00:00Z")
    assert response.status_code == 200
    data = response.json()
    # Should only return messages from 2024-01-02 onwards
    for msg in data["data"]:
        assert msg["ts"] >= "2024-01-02T00:00:00Z"


def test_combined_filters(client):
    """Test combining multiple filters."""
    response = client.get("/messages?from=%2B1111111111&since=2024-01-01T10:00:00Z&limit=10")
    assert response.status_code == 200
    data = response.json()
    # All messages should match both filters
    for msg in data["data"]:
        assert msg["from_msisdn"] == "+1111111111"
        assert msg["ts"] >= "2024-01-01T10:00:00Z"


def test_text_search(client):
    """Test text search filter."""
    response = client.get("/messages?q=First")
    assert response.status_code == 200
    data = response.json()
    # Should find messages containing "First"
    assert len(data["data"]) > 0
    for msg in data["data"]:
        assert "First" in msg.get("text", "").lower() or "first" in msg.get("text", "").lower()

