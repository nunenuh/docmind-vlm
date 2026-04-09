"""Conversation repository — CRUD operations for project conversations and messages."""

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import ProjectConversation, ProjectMessage

logger = get_logger(__name__)


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
