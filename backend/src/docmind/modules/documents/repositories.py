"""
docmind/modules/documents/repositories.py

Document database operations via SQLAlchemy.
All user-facing queries filter by user_id for ownership enforcement.
"""

from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    AuditEntry,
    ChatMessage,
    Citation,
    Document,
    ExtractedField,
    Extraction,
    PageChunk,
)

logger = get_logger(__name__)

_ALLOWED_STATUS_FIELDS = frozenset({"page_count", "document_type"})


class DocumentRepository:
    """Repository for document CRUD operations via SQLAlchemy."""

    async def create(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Document:
        """Insert a new document record. Returns the created ORM instance."""
        async with AsyncSessionLocal() as session:
            doc = Document(
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                storage_path=storage_path,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            return doc

    async def get_by_id(self, document_id: str, user_id: str) -> Document | None:
        """Get a single document by ID, scoped to user."""
        async with AsyncSessionLocal() as session:
            stmt = select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: str,
        page: int,
        limit: int,
        standalone_only: bool = False,
    ) -> tuple[list[Document], int]:
        """Get paginated documents for a user.

        Args:
            user_id: Owner user ID.
            page: Page number (1-based).
            limit: Items per page.
            standalone_only: If True, only return docs NOT linked to a project.

        Returns:
            Tuple of (items, total_count).
        """
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")

        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            base_filter = [Document.user_id == user_id]
            if standalone_only:
                base_filter.append(Document.project_id.is_(None))

            count_stmt = select(func.count()).select_from(Document).where(*base_filter)
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(Document)
                .where(*base_filter)
                .order_by(Document.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def delete(self, document_id: str, user_id: str) -> str | None:
        """Delete a document and all cascaded records explicitly.

        Cascade order (leaf → root):
        Citations → ChatMessages → AuditEntries/ExtractedFields → Extractions → Document
        """
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Document).where(
                    Document.id == document_id,
                    Document.user_id == user_id,
                )
                result = await session.execute(stmt)
                doc = result.scalar_one_or_none()
                if doc is None:
                    return None

                storage_path = doc.storage_path

                # Delete extraction children
                ext_stmt = select(Extraction.id).where(
                    Extraction.document_id == document_id
                )
                ext_result = await session.execute(ext_stmt)
                ext_ids = [row[0] for row in ext_result.all()]

                if ext_ids:
                    await session.execute(
                        sa_delete(AuditEntry).where(
                            AuditEntry.extraction_id.in_(ext_ids)
                        )
                    )
                    await session.execute(
                        sa_delete(ExtractedField).where(
                            ExtractedField.extraction_id.in_(ext_ids)
                        )
                    )

                # Delete chat message children (citations first)
                msg_stmt = select(ChatMessage.id).where(
                    ChatMessage.document_id == document_id
                )
                msg_result = await session.execute(msg_stmt)
                msg_ids = [row[0] for row in msg_result.all()]

                if msg_ids:
                    await session.execute(
                        sa_delete(Citation).where(
                            Citation.message_id.in_(msg_ids)
                        )
                    )

                await session.execute(
                    sa_delete(ChatMessage).where(
                        ChatMessage.document_id == document_id
                    )
                )
                await session.execute(
                    sa_delete(Extraction).where(
                        Extraction.document_id == document_id
                    )
                )

                # Delete RAG chunks
                await session.execute(
                    sa_delete(PageChunk).where(
                        PageChunk.document_id == document_id
                    )
                )

                await session.delete(doc)
                await session.commit()

                return storage_path
            except Exception:
                await session.rollback()
                raise

    async def update_status(
        self,
        document_id: str,
        status: str,
        **kwargs: object,
    ) -> None:
        """Update document status and optional fields (system-level, no user_id filter)."""
        unexpected = set(kwargs) - _ALLOWED_STATUS_FIELDS
        if unexpected:
            raise ValueError(
                f"update_status received unexpected fields: {unexpected}"
            )

        async with AsyncSessionLocal() as session:
            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status=status,
                    updated_at=datetime.now(timezone.utc),
                    **kwargs,
                )
            )
            await session.execute(stmt)
            await session.commit()
