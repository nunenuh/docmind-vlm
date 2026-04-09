"""Project conversation usecase — list, get, delete conversations."""

from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException

from ..protocols import ConversationRepositoryProtocol, ProjectRepositoryProtocol
from ..repositories import ConversationRepository, ProjectRepository
from ..schemas import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
)

logger = get_logger(__name__)


class ProjectConversationUseCase:
    """Orchestrates project conversation operations."""

    def __init__(
        self,
        repo: ProjectRepositoryProtocol | None = None,
        conv_repo: ConversationRepositoryProtocol | None = None,
    ) -> None:
        self.repo = repo or ProjectRepository()
        self.conv_repo = conv_repo or ConversationRepository()

    async def list_conversations(
        self, user_id: str, project_id: str
    ) -> list[ConversationResponse]:
        """List all conversations for a project."""
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return []

        conversations = await self.conv_repo.list_for_project(project_id, user_id)
        result = []
        for conv in conversations:
            msg_count = await self.conv_repo.get_message_count(str(conv.id))
            result.append(
                ConversationResponse(
                    id=str(conv.id),
                    title=conv.title,
                    message_count=msg_count,
                    created_at=conv.created_at,
                )
            )
        return result

    async def get_conversation(
        self, user_id: str, conversation_id: str
    ) -> ConversationDetailResponse:
        """Get a conversation with all messages."""
        conversation = await self.conv_repo.get_by_id(conversation_id, user_id)
        if conversation is None:
            raise NotFoundException("Conversation not found")

        return ConversationDetailResponse(
            id=str(conversation.id),
            title=conversation.title,
            messages=[
                MessageResponse(
                    id=str(msg.id),
                    role=msg.role,
                    content=msg.content,
                    citations=msg.citations,
                    created_at=msg.created_at,
                )
                for msg in conversation.messages
            ],
            created_at=conversation.created_at,
        )

    async def delete_conversation(
        self, user_id: str, conversation_id: str
    ) -> bool:
        """Delete a conversation and all its messages."""
        return await self.conv_repo.delete(conversation_id, user_id)
