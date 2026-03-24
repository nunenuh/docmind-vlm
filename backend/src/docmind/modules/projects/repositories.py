"""
docmind/modules/projects/repositories.py

Project and Conversation database operations via SQLAlchemy.
All user-facing queries filter by user_id for ownership enforcement.
"""

from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    Document,
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

                # Re-fetch to return updated state
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

                # Delete conversation messages first
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

                # Delete conversations
                await session.execute(
                    sa_delete(ProjectConversation).where(
                        ProjectConversation.project_id == project_id
                    )
                )

                # Unlink documents (set project_id to NULL instead of deleting)
                await session.execute(
                    update(Document)
                    .where(Document.project_id == project_id)
                    .values(project_id=None)
                )

                await session.delete(project)
                await session.commit()
                return True
            except Exception as e:
                logger.error("project_delete_failed: %s", e)
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
            # Verify project ownership first
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

    async def remove_document(self, project_id: str, document_id: str) -> bool:
        """Unlink a document from a project. Returns True if updated."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Document)
                .where(
                    Document.id == document_id,
                    Document.project_id == project_id,
                )
                .values(
                    project_id=None,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0  # type: ignore[union-attr]

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

        Returns:
            Tuple of (chunk_list, total_count).
        """
        async with AsyncSessionLocal() as session:
            filters = [PageChunk.project_id == project_id]
            if document_id:
                filters.append(PageChunk.document_id == document_id)

            count_stmt = select(func.count()).select_from(PageChunk).where(*filters)
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(PageChunk)
                .where(*filters)
                .order_by(PageChunk.page_number, PageChunk.chunk_index)
                .limit(limit)
            )
            result = await session.execute(stmt)
            chunks = list(result.scalars().all())

            return chunks, total


class ConversationRepository:
    """Repository for project conversation CRUD operations."""

    async def create(
        self,
        project_id: str,
        user_id: str,
        title: str | None = None,
    ) -> ProjectConversation:
        """Create a new conversation in a project."""
        async with AsyncSessionLocal() as session:
            conversation = ProjectConversation(
                project_id=project_id,
                user_id=user_id,
                title=title,
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[ProjectConversation]:
        """List all conversations for a project, scoped to user."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ProjectConversation)
                .where(
                    ProjectConversation.project_id == project_id,
                    ProjectConversation.user_id == user_id,
                )
                .order_by(ProjectConversation.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_id(
        self, conversation_id: str, user_id: str
    ) -> ProjectConversation | None:
        """Get a conversation by ID with messages eager loaded."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ProjectConversation)
                .options(selectinload(ProjectConversation.messages))
                .where(
                    ProjectConversation.id == conversation_id,
                    ProjectConversation.user_id == user_id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def delete(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and all its messages. Returns True if deleted."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(ProjectConversation).where(
                    ProjectConversation.id == conversation_id,
                    ProjectConversation.user_id == user_id,
                )
                result = await session.execute(stmt)
                conversation = result.scalar_one_or_none()
                if conversation is None:
                    return False

                await session.execute(
                    sa_delete(ProjectMessage).where(
                        ProjectMessage.conversation_id == conversation_id
                    )
                )
                await session.delete(conversation)
                await session.commit()
                return True
            except Exception as e:
                logger.error("conversation_delete_failed: %s", e)
                await session.rollback()
                raise

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: str | None = None,
    ) -> ProjectMessage:
        """Add a message to a conversation."""
        async with AsyncSessionLocal() as session:
            message = ProjectMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                citations=citations,
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message

    async def get_message_count(self, conversation_id: str) -> int:
        """Count messages in a conversation."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(ProjectMessage)
                .where(ProjectMessage.conversation_id == conversation_id)
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
