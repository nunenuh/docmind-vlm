"""Protocols for the chat module — structural contracts for DI."""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, Protocol

if TYPE_CHECKING:
    from docmind.core.database import ChatMessage
    from docmind.modules.chat.schemas import ChatHistoryResponse


class ChatRepositoryProtocol(Protocol):
    """Contract for chat message persistence."""

    async def create(
        self,
        document_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> ChatMessage: ...

    async def list_for_document(
        self,
        document_id: str,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[ChatMessage], int]: ...


class ChatServiceProtocol(Protocol):
    """Contract for per-document chat with VLM."""

    async def stream_response(
        self,
        document_id: str,
        user_id: str,
        message: str,
        history: list[dict],
        image: object | None = None,
    ) -> AsyncGenerator[str, None]: ...
