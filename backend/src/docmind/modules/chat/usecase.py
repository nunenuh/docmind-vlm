"""docmind/modules/chat/usecase.py — Stub."""
import json
from typing import AsyncGenerator

from docmind.core.logging import get_logger
from .schemas import ChatHistoryResponse

logger = get_logger(__name__)


class ChatUseCase:
    def send_message(self, document_id: str, user_id: str, message: str) -> AsyncGenerator[str, None]:
        return self._chat_stream(document_id, user_id, message)

    async def _chat_stream(self, document_id: str, user_id: str, message: str) -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'done', 'message_id': 'stub'})}\n\n"

    def get_history(self, document_id: str, user_id: str, page: int, limit: int) -> ChatHistoryResponse:
        return ChatHistoryResponse(items=[], total=0, page=page, limit=limit)
