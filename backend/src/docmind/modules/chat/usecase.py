"""
docmind/modules/chat/usecase.py

Chat use case — orchestrates chat pipeline, message persistence, and SSE streaming.
"""

import asyncio
import json
from typing import Any, AsyncGenerator

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.library.pipeline.chat import run_chat_pipeline

from .repositories import ChatRepository
from .schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
    Citation,
)

logger = get_logger(__name__)


class ChatUseCase:
    """Orchestrates chat operations across pipeline, repository, and service."""

    def __init__(self, repo: ChatRepository | None = None) -> None:
        self.repo = repo or ChatRepository()

    def send_message(
        self, document_id: str, user_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        return self._chat_stream(document_id, user_id, message)

    async def _load_context(
        self, document_id: str, user_id: str
    ) -> tuple[list[Any], list[dict], list[dict]]:
        """Load context for the chat pipeline.

        Returns:
            Tuple of (page_images, extracted_fields, conversation_history).
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

        # Page images would be loaded from storage in production
        page_images: list[Any] = []

        return page_images, extracted_fields, conversation_history

    async def _chat_stream(
        self, document_id: str, user_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        def _sse(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        # Persist user message
        await self.repo.save_message(document_id, user_id, "user", message)

        # Load context
        try:
            page_images, extracted_fields, conversation_history = await self._load_context(
                document_id, user_id
            )
        except Exception as e:
            logger.error("chat_context_load_failed: %s", e, exc_info=True)
            yield _sse({"type": "error", "message": "Failed to load document context"})
            return

        # Set up streaming queue
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def on_event(event_type: str, **kwargs: Any) -> None:
            queue.put_nowait({"type": event_type, **kwargs})

        initial_state: dict = {
            "document_id": document_id,
            "user_id": user_id,
            "message": message,
            "page_images": page_images,
            "extracted_fields": extracted_fields,
            "conversation_history": conversation_history,
            "intent": "",
            "intent_confidence": 0.0,
            "relevant_fields": [],
            "re_queried_regions": [],
            "raw_answer": "",
            "answer": "",
            "citations": [],
            "error_message": None,
            "stream_callback": on_event,
        }

        # Run pipeline in background thread
        pipeline_task = asyncio.create_task(
            asyncio.to_thread(run_chat_pipeline, initial_state)
        )

        # Yield SSE events
        try:
            while not pipeline_task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=get_settings().CHAT_HEARTBEAT_TIMEOUT)
                    if event is None:
                        break
                    yield _sse(event)
                except asyncio.TimeoutError:
                    yield _sse({"type": "heartbeat"})

            # Drain remaining events
            while not queue.empty():
                event = queue.get_nowait()
                if event is not None:
                    yield _sse(event)

            # Get pipeline result
            result = await pipeline_task
            answer = result.get("answer", "")
            citations = result.get("citations", [])

            # Persist assistant message
            msg_id = await self.repo.save_message(
                document_id, user_id, "assistant", answer, citations=citations
            )

            yield _sse({"type": "done", "message_id": msg_id})

        except Exception as e:
            logger.error("chat_stream_error: %s", e, exc_info=True)
            yield _sse({"type": "error", "message": "Chat processing failed"})

    async def get_history(
        self, document_id: str, user_id: str, page: int, limit: int
    ) -> ChatHistoryResponse:
        """Get paginated chat history.

        Args:
            document_id: The document ID.
            user_id: The user ID.
            page: Page number (1-based).
            limit: Items per page.

        Returns:
            ChatHistoryResponse with mapped messages and citations.
        """
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
