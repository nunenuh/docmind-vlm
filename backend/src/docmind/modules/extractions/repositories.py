"""
docmind/modules/extractions/repositories.py

Extraction database operations via SQLAlchemy.
"""

from sqlalchemy import select

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import AuditEntry, ExtractedField, Extraction

logger = get_logger(__name__)


class ExtractionRepository:
    """Repository for extraction query operations via SQLAlchemy."""

    async def get_latest_extraction(self, document_id: str) -> Extraction | None:
        """Get the most recent extraction for a document.

        Args:
            document_id: The document ID.

        Returns:
            Latest Extraction ORM instance, or None.
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Extraction)
                .where(Extraction.document_id == document_id)
                .order_by(Extraction.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_fields(self, extraction_id: str) -> list[ExtractedField]:
        """Get all extracted fields for an extraction, ordered by page and position.

        Args:
            extraction_id: The extraction ID.

        Returns:
            List of ExtractedField ORM instances.
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ExtractedField)
                .where(ExtractedField.extraction_id == extraction_id)
                .order_by(ExtractedField.page_number, ExtractedField.id)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_audit_trail(self, extraction_id: str) -> list[AuditEntry]:
        """Get audit entries for an extraction, ordered by step_order.

        Args:
            extraction_id: The extraction ID.

        Returns:
            List of AuditEntry ORM instances.
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AuditEntry)
                .where(AuditEntry.extraction_id == extraction_id)
                .order_by(AuditEntry.step_order)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
