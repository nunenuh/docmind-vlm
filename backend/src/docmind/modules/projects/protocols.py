"""Protocols for the projects module — structural contracts for DI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from docmind.core.database import (
        Document,
        Project,
        ProjectConversation,
        ProjectMessage,
    )


class ProjectRepositoryProtocol(Protocol):
    """Contract for project persistence."""

    async def create(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        persona_id: str | None = None,
    ) -> Project: ...

    async def get_by_id(
        self, project_id: str, user_id: str
    ) -> Project | None: ...

    async def list_for_user(
        self, user_id: str, page: int, limit: int
    ) -> tuple[list[Project], int]: ...

    async def update(
        self, project_id: str, user_id: str, **kwargs: object
    ) -> Project | None: ...

    async def delete(
        self, project_id: str, user_id: str
    ) -> bool: ...

    async def add_document(
        self, project_id: str, document_id: str
    ) -> bool: ...

    async def list_documents(
        self, project_id: str, user_id: str
    ) -> list[Document]: ...

    async def remove_document(
        self, project_id: str, document_id: str
    ) -> str | None: ...

    async def get_document_count(
        self, project_id: str
    ) -> int: ...

    async def list_chunks(
        self,
        project_id: str,
        document_id: str | None = None,
        limit: int = 100,
    ) -> tuple[list, int]: ...


class ConversationRepositoryProtocol(Protocol):
    """Contract for conversation persistence."""

    async def create(
        self,
        project_id: str,
        user_id: str,
        title: str | None = None,
    ) -> ProjectConversation: ...

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[ProjectConversation]: ...

    async def get_by_id(
        self, conversation_id: str, user_id: str
    ) -> ProjectConversation | None: ...

    async def delete(
        self, conversation_id: str, user_id: str
    ) -> bool: ...

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: str | None = None,
    ) -> ProjectMessage: ...

    async def get_message_count(
        self, conversation_id: str
    ) -> int: ...


class PromptServiceProtocol(Protocol):
    """Contract for prompt building."""

    def build_system_prompt(
        self,
        persona_name: str,
        persona_prompt: str,
        context: str,
        citations: list,
    ) -> str: ...

    def format_context(
        self, chunks: list[dict], citations: list
    ) -> str: ...

    def validate_persona_assignment(
        self, persona_id: str | None
    ) -> None: ...


class RAGServiceProtocol(Protocol):
    """Contract for RAG retrieval operations."""

    def embed_query(self, query: str) -> list[float]: ...

    def retrieve_chunks(
        self,
        project_id: str,
        query_embedding: list[float],
        query_text: str,
    ) -> list[dict]: ...

    def rewrite_query(
        self, message: str, history: list[dict]
    ) -> str: ...


class IndexingServiceProtocol(Protocol):
    """Contract for document RAG indexing."""

    def index(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> int: ...

    def reindex(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> int: ...


class VLMServiceProtocol(Protocol):
    """Contract for VLM streaming chat."""

    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: str,
    ) -> object: ...
