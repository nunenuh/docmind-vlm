"""PostgreSQL Async Engine.

Provides async SQLAlchemy engine for PostgreSQL connections.
Uses NullPool with connection retry for Supabase free tier resilience.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as sqlalchemy_create_async_engine
from sqlalchemy.pool import NullPool

from docmind.core.config import get_settings


def create_async_engine() -> AsyncEngine:
    """Create async PostgreSQL engine with retry-friendly settings.

    Uses NullPool (fresh connection per request) and increased
    connect timeout for Supabase free tier reliability.
    """
    settings = get_settings()
    return sqlalchemy_create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        echo=settings.APP_DEBUG,
        connect_args={
            "timeout": 30,
            "command_timeout": 30,
            "server_settings": {
                "statement_timeout": "30000",
            },
        },
    )


@lru_cache()
def get_async_engine() -> AsyncEngine:
    """Get cached async engine instance."""
    return create_async_engine()


# Module-level engine instance (lazy initialization)
async_engine = get_async_engine()
