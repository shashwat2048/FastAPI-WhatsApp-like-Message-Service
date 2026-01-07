"""
Tests for /stats endpoint:
- Statistics correctness
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
    """Set up test database before each test."""
    # Create temporary database
    test_db_path = os.path.join(tempfile.gettempdir(), f'test_stats_{os.getpid()}.db')
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
    
    yield
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


def test_stats_endpoint(client):
    """Test stats endpoint returns correct data."""
    # Insert some test messages
    test_messages = [
        {
            "message_id": "msg-001",
            "from_msisdn": "+1111111111",
            "to_msisdn": "+2222222222",
            "ts": "2024-01-01T10:00:00Z",
            "text": "Message 1",
            "created_at": "2024-01-01T10:00:00Z"
        },
        {
            "message_id": "msg-002",
            "from_msisdn": "+1111111111",
            "to_msisdn": "+3333333333",
            "ts": "2024-01-01T11:00:00Z",
            "text": "Message 2",
            "created_at": "2024-01-01T11:00:00Z"
        },
        {
            "message_id": "msg-003",
            "from_msisdn": "+4444444444",
            "to_msisdn": "+2222222222",
            "ts": "2024-01-01T12:00:00Z",
            "text": "Message 3",
            "created_at": "2024-01-01T12:00:00Z"
        },
    ]
    
    for msg in test_messages:
        insert_message(msg)
    
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "total_messages" in data
    assert "senders_count" in data
    assert "messages_per_sender" in data
    assert "first_message_ts" in data
    assert "last_message_ts" in data
    
    # Verify values
    assert data["total_messages"] == 3
    assert data["senders_count"] == 2
    assert len(data["messages_per_sender"]) <= 10
    assert data["first_message_ts"] == "2024-01-01T10:00:00Z"
    assert data["last_message_ts"] == "2024-01-01T12:00:00Z"


def test_stats_with_no_messages(client):
    """Test stats endpoint with no messages."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_messages"] == 0
    assert data["senders_count"] == 0
    assert data["messages_per_sender"] == []
    assert data["first_message_ts"] is None
    assert data["last_message_ts"] is None


def test_stats_accuracy(client):
    """Test that stats are calculated correctly."""
    # Insert messages from different senders
    messages = [
        {"message_id": f"msg-{i}", "from_msisdn": "+1111111111", "to_msisdn": "+2222222222",
         "ts": f"2024-01-01T{10+i:02d}:00:00Z", "text": f"Message {i}", "created_at": f"2024-01-01T{10+i:02d}:00:00Z"}
        for i in range(1, 6)
    ]
    messages.append({
        "message_id": "msg-6",
        "from_msisdn": "+3333333333",
        "to_msisdn": "+2222222222",
        "ts": "2024-01-01T16:00:00Z",
        "text": "Message 6",
        "created_at": "2024-01-01T16:00:00Z"
    })
    
    for msg in messages:
        insert_message(msg)
    
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    # Verify accuracy
    assert data["total_messages"] == 6
    assert data["senders_count"] == 2
    assert data["first_message_ts"] == "2024-01-01T11:00:00Z"
    assert data["last_message_ts"] == "2024-01-01T16:00:00Z"
    
    # Verify messages_per_sender is sorted descending
    if len(data["messages_per_sender"]) > 1:
        counts = [item["count"] for item in data["messages_per_sender"]]
        assert counts == sorted(counts, reverse=True)
    
    # Verify sum of messages_per_sender <= total_messages
    sum_counts = sum(item["count"] for item in data["messages_per_sender"])
    assert sum_counts <= data["total_messages"]

