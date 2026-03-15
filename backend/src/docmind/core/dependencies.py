"""
docmind/core/dependencies.py

FastAPI dependency functions for auth and database clients.
"""
from docmind.core.auth import get_current_user  # re-export
from docmind.dbase.sqlalchemy.engine import get_session  # re-export
from docmind.dbase.supabase.client import get_supabase_client  # re-export (Auth + Storage)

__all__ = ["get_current_user", "get_session", "get_supabase_client"]
