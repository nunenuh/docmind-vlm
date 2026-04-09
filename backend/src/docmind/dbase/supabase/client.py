"""
docmind/dbase/supabase/client.py

Supabase client initialization and singleton.
Used for Auth (JWT verification) and Storage (file upload/download) ONLY.
All database queries go through SQLAlchemy (dbase/psql/).
"""

from supabase import Client, create_client

from docmind.core.config import get_settings
from docmind.core.logging import get_logger

logger = get_logger(__name__)

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton (Auth + Storage only)."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SECRET_KEY,
        )
        logger.info("Supabase client initialized", url=settings.SUPABASE_URL)
    return _supabase_client
