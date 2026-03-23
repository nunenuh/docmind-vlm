"""
docmind/modules/analytics/repositories.py

Analytics repository — read-only aggregation queries.
"""

from sqlalchemy import select, func

from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    Document,
    PageChunk,
    Persona,
    Project,
)


class AnalyticsRepository:
    """Read-only repository for analytics aggregation queries."""

    async def count_documents(self, user_id: str) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count()).select_from(Document).where(Document.user_id == user_id)
            )
            return result.scalar() or 0

    async def count_documents_by_status(self, user_id: str) -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            counts: dict[str, int] = {}
            for status in ("uploaded", "processing", "ready", "error"):
                result = await session.execute(
                    select(func.count()).select_from(Document).where(
                        Document.user_id == user_id, Document.status == status
                    )
                )
                counts[status] = result.scalar() or 0
            return counts

    async def count_documents_by_type(self, user_id: str) -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document.file_type, func.count()).where(
                    Document.user_id == user_id
                ).group_by(Document.file_type)
            )
            return {row[0]: row[1] for row in result.all()}

    async def sum_pages(self, user_id: str) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.sum(Document.page_count)).where(Document.user_id == user_id)
            )
            return result.scalar() or 0

    async def sum_storage_bytes(self, user_id: str) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.sum(Document.file_size)).where(Document.user_id == user_id)
            )
            return result.scalar() or 0

    async def count_chunks(self, user_id: str) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count()).select_from(PageChunk).where(
                    PageChunk.project_id.in_(
                        select(Project.id).where(Project.user_id == user_id)
                    )
                )
            )
            return result.scalar() or 0

    async def count_projects(self, user_id: str) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count()).select_from(Project).where(Project.user_id == user_id)
            )
            return result.scalar() or 0

    async def count_custom_personas(self, user_id: str) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count()).select_from(Persona).where(
                    Persona.user_id == user_id, Persona.is_preset == False
                )
            )
            return result.scalar() or 0
