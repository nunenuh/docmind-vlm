"""PostgreSQL Async Engine.

Provides async SQLAlchemy engine for PostgreSQL connections.
Configured for Supabase compatibility (direct or pooler).

Key settings (from Supabase + asyncpg best practices):
- NullPool: fresh connection per request (let Supavisor manage pooling)
- statement_cache_size=0: prevents prepared statement conflicts
- prepared_statement_cache_size=0: same, for SQLAlchemy layer
- pool_pre_ping=True: validate connections before use
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as sqlalchemy_create_async_engine
from sqlalchemy.pool import NullPool

from docmind.core.config import get_settings


def create_async_engine() -> AsyncEngine:
    """Create async PostgreSQL engine optimized for Supabase.

    Works with both direct connection (port 5432) and
    Supavisor pooler (port 6543).
    """
    settings = get_settings()
    timeout = settings.DB_CONNECT_TIMEOUT
    return sqlalchemy_create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        echo=settings.APP_DEBUG,
        pool_pre_ping=True,
        connect_args={
            # Disable prepared statement caching (required for Supabase pooler)
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            # Connection timeout from settings
            "timeout": timeout,
            "command_timeout": timeout,
            "server_settings": {
                "statement_timeout": str(timeout * 1000),
            },
        },
    )


@lru_cache()
def get_async_engine() -> AsyncEngine:
    """Get cached async engine instance."""
    return create_async_engine()


# Module-level engine instance (lazy initialization)
async_engine = get_async_engine()
