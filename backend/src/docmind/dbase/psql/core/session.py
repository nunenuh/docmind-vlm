"""PostgreSQL Session Management.

Provides async session factory for FastAPI dependency injection.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import get_async_engine

AsyncSessionLocal = async_sessionmaker(
    bind=get_async_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for FastAPI dependency injection.

    Yields:
        AsyncSession: SQLAlchemy async session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
