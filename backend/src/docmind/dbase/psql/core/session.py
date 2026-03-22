"""PostgreSQL Session Management.

Provides async session factory with retry logic for Supabase reliability.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind.core.config import get_settings
from .engine import get_async_engine

logger = logging.getLogger(__name__)

_session_factory = async_sessionmaker(
    bind=get_async_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def _session_with_retry() -> AsyncGenerator[AsyncSession, None]:
    """Create a session with automatic retry on connection failure."""
    settings = get_settings()
    max_retries = settings.DB_MAX_RETRIES
    retry_delay = settings.DB_RETRY_DELAY

    last_error = None
    for attempt in range(max_retries):
        try:
            async with _session_factory() as session:
                yield session
                return
        except (TimeoutError, OSError, ConnectionError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = retry_delay * (2 ** attempt)
                logger.warning(
                    "DB connection failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, max_retries, wait, e,
                )
                await asyncio.sleep(wait)
            else:
                logger.error("DB connection failed after %d attempts: %s", max_retries, e)
                raise
    raise last_error  # type: ignore


AsyncSessionLocal = _session_with_retry


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
