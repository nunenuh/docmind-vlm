"""
docmind/modules/chat/repositories.py

Chat database operations via SQLAlchemy.
"""

from sqlalchemy import func, select

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    ChatMessage,
    Citation,
    ExtractedField,
    Extraction,
)

logger = get_logger(__name__)


class ChatRepository:
    """Repository for chat message CRUD operations via SQLAlchemy."""

    async def save_message(
        self,
        document_id: str,
        user_id: str,
        role: str,
        content: str,
        citations: list[dict] | None = None,
    ) -> str:
        """Create a chat message with optional citations.

        Args:
            document_id: The document ID.
            user_id: The user ID.
            role: Message role ("user" or "assistant").
            content: Message content text.
            citations: Optional list of citation dicts.

        Returns:
            The created message ID string.
        """
        async with AsyncSessionLocal() as session:
            message = ChatMessage(
                document_id=document_id,
                user_id=user_id,
                role=role,
                content=content,
            )
            session.add(message)

            if citations:
                for c in citations:
                    citation = Citation(
                        message_id=message.id,
                        page=c.get("page", 1),
                        bounding_box=c.get("bounding_box", {}),
                        text_span=c.get("text_span", ""),
                    )
                    session.add(citation)

            await session.commit()
            return str(message.id)

    async def get_history(
        self,
        document_id: str,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[ChatMessage], int]:
        """Get paginated chat history for a document.

        Args:
            document_id: The document ID.
            user_id: The user ID.
            page: Page number (1-based).
            limit: Items per page.

        Returns:
            Tuple of (items, total_count).
        """
        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            count_stmt = (
                select(func.count())
                .select_from(ChatMessage)
                .where(
                    ChatMessage.document_id == document_id,
                    ChatMessage.user_id == user_id,
                )
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.document_id == document_id,
                    ChatMessage.user_id == user_id,
                )
                .order_by(ChatMessage.created_at.asc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def get_recent_messages(
        self,
        document_id: str,
        user_id: str,
        limit: int = 20,
    ) -> list[ChatMessage]:
        """Get the most recent messages for conversation context.

        Args:
            document_id: The document ID.
            user_id: The user ID.
            limit: Maximum number of messages.

        Returns:
            List of ChatMessage ORM instances, ordered by created_at ASC.
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.document_id == document_id,
                    ChatMessage.user_id == user_id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = list(result.scalars().all())
            messages.reverse()  # Return in chronological order
            return messages

    async def get_extracted_fields(
        self, document_id: str
    ) -> list[ExtractedField]:
        """Get extracted fields for the latest extraction of a document.

        Args:
            document_id: The document ID.

        Returns:
            List of ExtractedField ORM instances, or empty list.
        """
        async with AsyncSessionLocal() as session:
            # Find latest extraction ID
            ext_stmt = (
                select(Extraction.id)
                .where(Extraction.document_id == document_id)
                .order_by(Extraction.created_at.desc())
                .limit(1)
            )
            ext_id = (await session.execute(ext_stmt)).scalar_one_or_none()

            if ext_id is None:
                return []

            # Get fields
            fields_stmt = (
                select(ExtractedField)
                .where(ExtractedField.extraction_id == ext_id)
                .order_by(ExtractedField.page_number)
            )
            result = await session.execute(fields_stmt)
            return list(result.scalars().all())
