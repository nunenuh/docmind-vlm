"""
docmind/modules/chat/usecase.py

Chat use case — orchestrates per-document chat with VLM streaming + thinking.
Uses extracted fields as context for grounded answers.
"""

import json
from typing import AsyncGenerator

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.library.providers.factory import get_vlm_provider

from .repositories import ChatRepository
from .schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
    Citation,
)
from .services import ChatService

logger = get_logger(__name__)

class ChatUseCase:
    """Orchestrates per-document chat with VLM streaming."""

    def __init__(
        self,
        repo: ChatRepository | None = None,
        service: ChatService | None = None,
    ) -> None:
        self.repo = repo or ChatRepository()
        self.service = service or ChatService()

    def send_message(
        self, document_id: str, user_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        return self._chat_stream(document_id, user_id, message)

    async def _load_context(
        self, document_id: str, user_id: str
    ) -> tuple[list[dict], list[dict]]:
        """Load extracted fields and conversation history.

        Returns:
            Tuple of (extracted_fields, conversation_history).
        """
        extracted_fields_orm = await self.repo.get_extracted_fields(document_id)
        extracted_fields = [
            {
                "field_key": f.field_key,
                "field_value": f.field_value,
                "page_number": f.page_number,
                "confidence": f.confidence,
                "bounding_box": f.bounding_box or {},
                "is_required": f.is_required,
            }
            for f in extracted_fields_orm
        ]

        recent = await self.repo.get_recent_messages(document_id, user_id, limit=20)
        conversation_history = [
            {"role": m.role, "content": m.content}
            for m in recent
        ]

        return extracted_fields, conversation_history

    def _format_fields(self, fields: list[dict]) -> str:
        """Delegate to service for field formatting."""
        return self.service.format_extracted_fields(fields)

    async def _chat_stream(
        self, document_id: str, user_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        settings = get_settings()

        def _sse(event: str, data: dict) -> str:
            return f"data: {json.dumps({'event': event, **data})}\n\n"

        # Persist user message
        await self.repo.save_message(document_id, user_id, "user", message)

        # Load context
        try:
            extracted_fields, conversation_history = await self._load_context(
                document_id, user_id
            )
        except Exception as e:
            logger.error("chat_context_load_failed: %s", e, exc_info=True)
            yield _sse("error", {"message": "Failed to load document context"})
            return

        yield _sse("status", {"message": "Loading document context..."})

        # Build system prompt with extracted fields
        fields_text = self._format_fields(extracted_fields)
        system_prompt = self.service.build_system_prompt(fields_text)

        yield _sse("status", {"message": "Generating response..."})

        # Stream with thinking
        provider = get_vlm_provider()
        full_answer = ""
        full_thinking = ""

        try:
            async for event in provider.chat_stream(
                images=[],
                message=message,
                history=conversation_history[-6:],
                system_prompt=system_prompt,
                enable_thinking=settings.ENABLE_THINKING,
            ):
                if event["type"] == "thinking":
                    full_thinking += event["content"]
                    yield _sse("thinking", {"content": event["content"]})
                elif event["type"] == "answer":
                    full_answer += event["content"]
                    yield _sse("token", {"content": event["content"]})
                elif event["type"] == "done":
                    pass

        except Exception as e:
            logger.error("chat_stream_error: %s", e, exc_info=True)
            full_answer = "I encountered an error while processing your question. Please try again."
            yield _sse("token", {"content": full_answer})

        # Persist assistant message
        msg_id = await self.repo.save_message(
            document_id, user_id, "assistant", full_answer
        )

        yield _sse("answer", {"content": full_answer})
        yield _sse("done", {"message_id": msg_id})

    async def get_history(
        self, document_id: str, user_id: str, page: int, limit: int
    ) -> ChatHistoryResponse:
        """Get paginated chat history."""
        items_orm, total = await self.repo.get_history(
            document_id, user_id, page, limit
        )

        items = [
            ChatMessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                citations=[
                    Citation(
                        page=c.page,
                        bounding_box=c.bounding_box or {},
                        text_span=c.text_span,
                    )
                    for c in (m.citations or [])
                ],
                created_at=m.created_at,
            )
            for m in items_orm
        ]

        return ChatHistoryResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
        )
