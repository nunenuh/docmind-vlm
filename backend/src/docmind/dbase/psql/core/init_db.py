"""PostgreSQL Database Initialization.

Provides functions to initialize the PostgreSQL database
and create all required tables.
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from .base import Base
from .engine import get_async_engine


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Initialize PostgreSQL database with all required tables.

    Args:
        engine: Optional async engine. Uses default if not provided.

    Note:
        For production, use Alembic migrations instead.
    """
    if engine is None:
        engine = get_async_engine()

    async with engine.begin() as conn:
        # Import all models to ensure they are registered with Base
        from .. import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables(engine: AsyncEngine | None = None) -> None:
    """Drop all PostgreSQL tables. USE WITH CAUTION.

    Args:
        engine: Optional async engine. Uses default if not provided.
    """
    if engine is None:
        engine = get_async_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
