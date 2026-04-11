"""
docmind/modules/chat/usecase.py

Chat use case — orchestrates per-document chat.
High-level business logic: load context, delegate to service, persist result.
NEVER calls library directly.
"""

import json
from typing import AsyncGenerator

from docmind.core.logging import get_logger

from docmind.modules.documents.repositories import DocumentRepository
from docmind.modules.documents.services import DocumentStorageService

from .repositories import ChatRepository
from .schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
    Citation,
)
from .services import ChatService

logger = get_logger(__name__)

IMAGE_FILE_TYPES = frozenset({"png", "jpg", "jpeg", "webp", "tiff"})


class ChatUseCase:
    """Orchestrates per-document chat."""

    def __init__(
        self,
        repo: ChatRepository | None = None,
        service: ChatService | None = None,
        doc_repo: DocumentRepository | None = None,
        storage_service: DocumentStorageService | None = None,
    ) -> None:
        self.repo = repo or ChatRepository()
        self.doc_repo = doc_repo or DocumentRepository()
        self.storage_service = storage_service or DocumentStorageService()
        self.service = service or ChatService()

    def send_message(
        self, document_id: str, user_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        return self._chat_stream(document_id, user_id, message)

    async def _chat_stream(
        self, document_id: str, user_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        def _sse(event: str, data: dict) -> str:
            return f"data: {json.dumps({'event': event, **data})}\n\n"

        # Persist user message
        await self.repo.save_message(document_id, user_id, "user", message)

        # Load context from repository
        try:
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
        except Exception as e:
            logger.error("chat_context_load_failed: %s", e, exc_info=True)
            yield _sse("error", {"message": "Failed to load document context"})
            return

        yield _sse("status", {"message": "Loading document context..."})

        # Load document image for visual grounding (if image type)
        import asyncio
        document_image = None
        try:
            doc = await self.doc_repo.get_by_id(document_id, user_id)
            if doc and doc.file_type in IMAGE_FILE_TYPES:
                document_image = await asyncio.to_thread(
                    self.storage_service.load_document_image,
                    doc.storage_path, doc.file_type,
                )
                if document_image is not None:
                    logger.info("Loaded document image for visual chat", document_id=document_id)
        except Exception as e:
            logger.warning("Failed to load document image: %s", e)

        # Delegate prompt building to service
        fields_text = self.service.format_extracted_fields(extracted_fields)
        system_prompt = self.service.build_system_prompt(fields_text)
        if document_image is not None:
            system_prompt += (
                "\n\nYou can see the actual document image. Use both the extracted fields "
                "AND the image to answer questions. If asked about visual details not in "
                "the extracted fields, describe what you see in the image."
            )
        history_slice = self.service.get_history_slice(conversation_history)

        # Resolve user provider override
        from docmind.shared.provider_resolver import resolve_provider_override

        vlm_override = await resolve_provider_override(user_id, "vlm")

        yield _sse("status", {"message": "Generating response..."})

        # Delegate VLM streaming to service (with image if available)
        full_answer = ""
        try:
            async for event in self.service.stream_chat(
                message=message,
                system_prompt=system_prompt,
                history=history_slice,
                document_image=document_image,
                override=vlm_override,
            ):
                if event["type"] == "thinking":
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
