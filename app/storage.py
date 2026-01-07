"""
Database operations for message storage.
"""
import sqlite3
from typing import Dict, Any, List, Tuple, Optional
from app.models import init_db


def get_db_connection() -> sqlite3.Connection:
    """
    Get a database connection.
    
    Returns:
        SQLite database connection
    """
    return init_db()


def insert_message(data: Dict[str, Any]) -> str:
    """
    Insert a message into the database.
    Idempotent via PRIMARY KEY message_id.
    
    Args:
        data: Dictionary containing message data with keys:
            - message_id: Unique message identifier (required)
            - from_msisdn: Sender phone number (required)
            - to_msisdn: Recipient phone number (required)
            - ts: Timestamp string (required)
            - text: Message text (optional)
            - created_at: Creation timestamp string (required)
    
    Returns:
        "created" if message was inserted, "duplicate" if message_id already exists
    """
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["message_id"],
            data["from_msisdn"],
            data["to_msisdn"],
            data["ts"],
            data.get("text"),
            data["created_at"]
        ))
        conn.commit()
        conn.close()
        return "created"
    except sqlite3.IntegrityError:
        # Duplicate message_id - idempotency handled via PRIMARY KEY
        conn.rollback()
        conn.close()
        return "duplicate"
    except Exception:
        # Ensure connection is closed even on unexpected errors
        conn.close()
        raise


def list_messages(
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    List messages with filtering, pagination, and ordering.
    
    Args:
        filters: Dictionary with optional filter keys:
            - from_msisdn: Filter by sender phone number
            - since: Filter messages where ts >= since (timestamp string)
            - q: Case-insensitive text search in message text
        limit: Maximum number of rows to return
        offset: Number of rows to skip
    
    Returns:
        Tuple of (rows, total_count) where:
        - rows: List of message dictionaries
        - total_count: Total number of messages matching filters
    """
    conn = get_db_connection()
    
    # Build WHERE clause
    conditions = []
    params = []
    
    if filters:
        if "from_msisdn" in filters and filters["from_msisdn"]:
            conditions.append("from_msisdn = ?")
            params.append(filters["from_msisdn"])
        
        if "since" in filters and filters["since"]:
            conditions.append("ts >= ?")
            params.append(filters["since"])
        
        if "q" in filters and filters["q"]:
            conditions.append("LOWER(text) LIKE ?")
            params.append(f"%{filters['q'].lower()}%")
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Get total count
    count_query = f"SELECT COUNT(*) as total FROM messages{where_clause}"
    total = conn.execute(count_query, params).fetchone()["total"]
    
    # Get paginated results with ordering: ts ASC, message_id ASC
    query = f"""
        SELECT message_id, from_msisdn, to_msisdn, ts, text, created_at
        FROM messages
        {where_clause}
        ORDER BY ts ASC, message_id ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    rows = conn.execute(query, params).fetchall()
    
    # Convert rows to dictionaries
    result_rows = [
        {
            "message_id": row["message_id"],
            "from_msisdn": row["from_msisdn"],
            "to_msisdn": row["to_msisdn"],
            "ts": row["ts"],
            "text": row["text"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]
    
    conn.close()
    return (result_rows, total)


def compute_stats() -> Dict[str, Any]:
    """
    Compute aggregated statistics about messages.
    
    Returns:
        Dictionary with aggregated statistics
    """
    conn = get_db_connection()
    
    # Total messages
    total = conn.execute("SELECT COUNT(*) as total FROM messages").fetchone()["total"]
    
    # Unique senders
    unique_senders = conn.execute(
        "SELECT COUNT(DISTINCT from_msisdn) as count FROM messages"
    ).fetchone()["count"]
    
    # Unique recipients
    unique_recipients = conn.execute(
        "SELECT COUNT(DISTINCT to_msisdn) as count FROM messages"
    ).fetchone()["count"]
    
    # Messages with text vs without text
    messages_with_text = conn.execute(
        "SELECT COUNT(*) as count FROM messages WHERE text IS NOT NULL AND text != ''"
    ).fetchone()["count"]
    
    messages_without_text = total - messages_with_text
    
    conn.close()
    
    return {
        "total": total,
        "unique_senders": unique_senders,
        "unique_recipients": unique_recipients,
        "messages_with_text": messages_with_text,
        "messages_without_text": messages_without_text
    }

