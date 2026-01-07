"""
Health router.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/live")
async def liveness():
    """Liveness probe endpoint - always returns 200."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """
    Readiness probe endpoint.
    Returns 200 only if:
    - DB is reachable
    - messages table exists
    - WEBHOOK_SECRET is set
    Otherwise returns 503.
    """
    from app.config import settings
    from app.models import parse_database_url
    import sqlite3
    
    # Check if WEBHOOK_SECRET is configured
    if not settings.WEBHOOK_SECRET:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": "WEBHOOK_SECRET is not configured"}
        )
    
    # Check database connection and messages table existence
    try:
        # Connect to database without creating tables
        db_path = parse_database_url(settings.DATABASE_URL)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check if database is reachable
        conn.execute("SELECT 1")
        
        # Check if messages table exists (without creating it)
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='messages'
        """)
        table_exists = cursor.fetchone() is not None
        
        conn.close()
        
        if not table_exists:
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "error": "messages table does not exist"}
            )
        
        return {"status": "ready"}
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": f"Database error: {str(e)}"}
        )

