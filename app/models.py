"""
SQLite database models and initialization.
"""
import sqlite3
from pathlib import Path
from app.config import settings


def parse_database_url(database_url: str) -> str:
    """
    Parse DATABASE_URL to extract SQLite file path.
    
    Examples:
        sqlite:////data/app.db -> /data/app.db
        sqlite:///./messages.db -> ./messages.db
        sqlite:///messages.db -> messages.db
    
    Args:
        database_url: Database URL string
        
    Returns:
        File path to SQLite database
    """
    # Remove sqlite:// prefix
    if database_url.startswith('sqlite:///'):
        path = database_url[10:]  # Remove 'sqlite:///'
    elif database_url.startswith('sqlite://'):
        path = database_url[9:]   # Remove 'sqlite://'
    else:
        # Not a sqlite URL, return as-is
        return database_url
    
    # Handle absolute paths (starting with /)
    # sqlite:////absolute/path -> /absolute/path
    if path.startswith('/'):
        return path
    
    # Handle relative paths
    return path


def init_db() -> sqlite3.Connection:
    """
    Initialize SQLite database and create schema.
    Creates the messages table if it doesn't exist.
    
    Returns:
        Database connection
    """
    # Parse DATABASE_URL to get file path
    db_path = parse_database_url(settings.DATABASE_URL)
    
    # Create parent directories if they don't exist
    # Handle read-only filesystem gracefully (e.g., in Docker with mounted volumes)
    db_file = Path(db_path)
    if not db_file.parent.exists():
        try:
            db_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Directory may be created by Docker/mounts, or filesystem is read-only
            # Continue - SQLite will create the file if parent exists or is accessible
            pass
    
    # Connect to database
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Create messages table with exact schema
    # Note: TEXT PRIMARY KEY in SQLite doesn't enforce NOT NULL automatically,
    # so we explicitly add NOT NULL to message_id
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY NOT NULL,
            from_msisdn TEXT NOT NULL,
            to_msisdn TEXT NOT NULL,
            ts TEXT NOT NULL,
            text TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    return conn


def init_schema():
    """
    Initialize database schema on startup.
    This function should be called when the application starts.
    Handles errors gracefully for cases where database directory doesn't exist yet.
    """
    try:
        conn = init_db()
        conn.close()
    except sqlite3.OperationalError as e:
        # Database file or directory may not exist yet (e.g., in Docker with mounted volumes)
        # Log warning but don't crash startup - database will be created on first use
        import logging
        logger = logging.getLogger("app")
        logger.warning(f"Could not initialize database schema: {e}. Database will be created on first use.")
        # Don't re-raise - allow app to start, database will be created on first access

