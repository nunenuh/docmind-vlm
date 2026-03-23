"""
docmind/modules/analytics/usecase.py

Analytics use case — aggregates stats from repositories.
"""

from sqlalchemy import select, func

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    Document,
    PageChunk,
    Project,
    Persona,
)

logger = get_logger(__name__)


class AnalyticsUseCase:
    """Aggregates platform analytics for a user."""

    async def get_summary(self, user_id: str) -> dict:
        """Get analytics summary for dashboard.

        Args:
            user_id: Authenticated user ID.

        Returns:
            Dict with documents, pages, storage, chunks, projects, personas stats.
        """
        async with AsyncSessionLocal() as session:
            # Documents
            doc_count = (await session.execute(
                select(func.count()).select_from(Document).where(Document.user_id == user_id)
            )).scalar() or 0

            # By status
            status_counts = {}
            for status in ["uploaded", "processing", "ready", "error"]:
                count = (await session.execute(
                    select(func.count()).select_from(Document).where(
                        Document.user_id == user_id, Document.status == status
                    )
                )).scalar() or 0
                status_counts[status] = count

            # By type
            type_rows = (await session.execute(
                select(Document.file_type, func.count()).where(
                    Document.user_id == user_id
                ).group_by(Document.file_type)
            )).all()
            type_counts = {row[0]: row[1] for row in type_rows}

            # Pages
            total_pages = (await session.execute(
                select(func.sum(Document.page_count)).where(Document.user_id == user_id)
            )).scalar() or 0

            # Storage
            total_storage = (await session.execute(
                select(func.sum(Document.file_size)).where(Document.user_id == user_id)
            )).scalar() or 0

            # RAG chunks
            chunk_count = (await session.execute(
                select(func.count()).select_from(PageChunk).where(
                    PageChunk.project_id.in_(
                        select(Project.id).where(Project.user_id == user_id)
                    )
                )
            )).scalar() or 0

            # Projects
            project_count = (await session.execute(
                select(func.count()).select_from(Project).where(Project.user_id == user_id)
            )).scalar() or 0

            # Custom personas
            persona_count = (await session.execute(
                select(func.count()).select_from(Persona).where(
                    Persona.user_id == user_id, Persona.is_preset == False
                )
            )).scalar() or 0

        return {
            "documents": {
                "total": doc_count,
                "by_status": status_counts,
                "by_type": type_counts,
            },
            "pages_processed": total_pages,
            "storage_bytes": total_storage,
            "storage_mb": round(total_storage / (1024 * 1024), 2) if total_storage else 0,
            "rag_chunks": chunk_count,
            "projects": project_count,
            "custom_personas": persona_count,
        }
