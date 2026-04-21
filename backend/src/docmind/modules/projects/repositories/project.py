"""Project repository — CRUD operations for projects and document linking."""

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
    Project,
    ProjectConversation,
    ProjectMessage,
)

logger = get_logger(__name__)


class ProjectRepository:
    """Repository for project CRUD operations via SQLAlchemy."""

    async def create(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        persona_id: str | None = None,
    ) -> Project:
        """Insert a new project record. Returns the created ORM instance."""
        async with AsyncSessionLocal() as session:
            project = Project(
                user_id=user_id,
                name=name,
                description=description,
                persona_id=persona_id,
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            return project

    async def get_by_id(self, project_id: str, user_id: str) -> Project | None:
        """Get a single project by ID, scoped to user."""
        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[Project], int]:
        """Get paginated projects for a user. Returns (items, total_count)."""
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")

        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            count_stmt = (
                select(func.count())
                .select_from(Project)
                .where(Project.user_id == user_id)
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(Project)
                .where(Project.user_id == user_id)
                .order_by(Project.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def update(
        self,
        project_id: str,
        user_id: str,
        **kwargs: object,
    ) -> Project | None:
        """Update a project. Returns updated project or None if not found."""
        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()
            if project is None:
                return None

            values = {k: v for k, v in kwargs.items() if v is not None}
            if values:
                values["updated_at"] = datetime.now(timezone.utc)
                update_stmt = (
                    update(Project)
                    .where(Project.id == project_id, Project.user_id == user_id)
                    .values(**values)
                )
                await session.execute(update_stmt)
                await session.commit()

                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

            return project

    async def delete(self, project_id: str, user_id: str) -> bool:
        """Delete a project and all cascaded records. Returns True if deleted."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Project).where(
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()
                if project is None:
                    return False

                conv_stmt = select(ProjectConversation.id).where(
                    ProjectConversation.project_id == project_id
                )
                conv_result = await session.execute(conv_stmt)
                conv_ids = [row[0] for row in conv_result.all()]

                if conv_ids:
                    await session.execute(
                        sa_delete(ProjectMessage).where(
                            ProjectMessage.conversation_id.in_(conv_ids)
                        )
                    )

                await session.execute(
                    sa_delete(ProjectConversation).where(
                        ProjectConversation.project_id == project_id
                    )
                )

                # Delete all RAG chunks for this project (issue #104).
                # ChunkEmbedding cascades via PageChunk.id FK.
                # Documents themselves remain, becoming standalone.
                await session.execute(
                    sa_delete(PageChunk).where(
                        PageChunk.project_id == project_id
                    )
                )

                await session.execute(
                    update(Document)
                    .where(Document.project_id == project_id)
                    .values(project_id=None)
                )

                await session.delete(project)
                await session.commit()
                return True
            except Exception as e:
                logger.error("project_delete_failed", project_id=project_id, error=str(e), exc_info=True)
                await session.rollback()
                raise

    async def add_document(self, project_id: str, document_id: str) -> bool:
        """Link a document to a project. Returns True if updated."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(
                    project_id=project_id,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0  # type: ignore[union-attr]

    async def list_documents(
        self, project_id: str, user_id: str
    ) -> list[Document]:
        """List all documents linked to a project."""
        async with AsyncSessionLocal() as session:
            proj_stmt = select(Project.id).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            proj_result = await session.execute(proj_stmt)
            if proj_result.scalar_one_or_none() is None:
                return []

            stmt = (
                select(Document)
                .where(Document.project_id == project_id)
                .order_by(Document.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def remove_document(
        self, project_id: str, document_id: str
    ) -> str | None:
        """Fully delete a document attached to a project (issue #104).

        Removes the Document and all dependent rows (PageChunks,
        ChunkEmbeddings via CASCADE, Extractions + children, ChatMessages +
        Citations). Caller is responsible for removing the storage file using
        the returned storage_path.

        Args:
            project_id: Project the document must be linked to.
            document_id: Document to delete.

        Returns:
            The document's storage_path if deleted; None if the document is
            not found or not linked to the given project.
        """
        async with AsyncSessionLocal() as session:
            try:
                doc_stmt = select(Document).where(
                    Document.id == document_id,
                    Document.project_id == project_id,
                )
                doc_result = await session.execute(doc_stmt)
                doc = doc_result.scalar_one_or_none()
                if doc is None:
                    return None

                storage_path = doc.storage_path

                ext_stmt = select(Extraction.id).where(
                    Extraction.document_id == document_id
                )
                ext_result = await session.execute(ext_stmt)
                ext_ids = [row[0] for row in ext_result.all()]

                msg_stmt = select(ChatMessage.id).where(
                    ChatMessage.document_id == document_id
                )
                msg_result = await session.execute(msg_stmt)
                msg_ids = [row[0] for row in msg_result.all()]

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
                    await session.execute(
                        sa_delete(Extraction).where(
                            Extraction.document_id == document_id
                        )
                    )

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

                # PageChunks cascade to ChunkEmbedding via ON DELETE CASCADE
                # (see chunk_embedding.chunk_id FK). ChunkEmbedding.document_id
                # FK also cascades after the CASCADE migration.
                await session.execute(
                    sa_delete(PageChunk).where(
                        PageChunk.document_id == document_id
                    )
                )

                await session.delete(doc)
                await session.commit()

                return storage_path
            except Exception as e:
                logger.error(
                    "project_remove_document_failed",
                    project_id=project_id,
                    document_id=document_id,
                    error=str(e),
                    exc_info=True,
                )
                await session.rollback()
                raise

    async def get_document_count(self, project_id: str) -> int:
        """Count documents linked to a project."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(Document)
                .where(Document.project_id == project_id)
            )
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def list_chunks(
        self, project_id: str, document_id: str | None = None, limit: int = 100
    ) -> tuple[list, int]:
        """List RAG chunks for a project, optionally filtered by document.

        JOINs Document to exclude orphaned chunks whose document was deleted
        (defense-in-depth for issue #104).
        """
        async with AsyncSessionLocal() as session:
            filters = [PageChunk.project_id == project_id]
            if document_id:
                filters.append(PageChunk.document_id == document_id)

            # JOIN Document and require it is still attached to the same
            # project, so orphan chunks from unlinked docs (issue #104
            # leftover) cannot leak into the list.
            join_on = (
                (Document.id == PageChunk.document_id)
                & (Document.project_id == PageChunk.project_id)
            )

            count_stmt = (
                select(func.count())
                .select_from(PageChunk)
                .join(Document, join_on)
                .where(*filters)
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(PageChunk)
                .join(Document, join_on)
                .where(*filters)
                .order_by(PageChunk.page_number, PageChunk.chunk_index)
                .limit(limit)
            )
            result = await session.execute(stmt)
            chunks = list(result.scalars().all())

            return chunks, total
