"""
docmind/modules/analytics/usecase.py

Analytics use case — orchestrates repository queries and service formatting.
"""

from docmind.core.logging import get_logger

from .repositories import AnalyticsRepository
from .services import AnalyticsService

logger = get_logger(__name__)


class AnalyticsUseCase:
    """Orchestrates analytics aggregation."""

    def __init__(self) -> None:
        self.repo = AnalyticsRepository()
        self.service = AnalyticsService()

    async def get_summary(self, user_id: str) -> dict:
        """Get analytics summary for dashboard.

        Args:
            user_id: Authenticated user ID.

        Returns:
            Formatted analytics dict.
        """
        doc_count = await self.repo.count_documents(user_id)
        status_counts = await self.repo.count_documents_by_status(user_id)
        type_counts = await self.repo.count_documents_by_type(user_id)
        total_pages = await self.repo.sum_pages(user_id)
        total_storage = await self.repo.sum_storage_bytes(user_id)
        chunk_count = await self.repo.count_chunks(user_id)
        project_count = await self.repo.count_projects(user_id)
        persona_count = await self.repo.count_custom_personas(user_id)

        return self.service.format_summary(
            doc_count=doc_count,
            status_counts=status_counts,
            type_counts=type_counts,
            total_pages=total_pages,
            total_storage=total_storage,
            chunk_count=chunk_count,
            project_count=project_count,
            persona_count=persona_count,
        )
