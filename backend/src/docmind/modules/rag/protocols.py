"""Protocols for the RAG module — structural contracts for DI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from docmind.core.database import PageChunk
    from docmind.modules.rag.schemas import (
        ChunkListResult,
        ChunkResult,
        CitationInfo,
        IndexResult,
        RetrievalResult,
    )


class ChunkRepositoryProtocol(Protocol):
    """Contract for chunk persistence."""

    async def list_by_project(
        self,
        project_id: str,
        document_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[PageChunk], int]: ...

    async def get_by_id(
        self, chunk_id: str, project_id: str
    ) -> PageChunk: ...

    async def count_by_project(self, project_id: str) -> int: ...

    async def count_by_document(self, document_id: str) -> int: ...

    async def get_existing_hashes(
        self, project_id: str
    ) -> set[str]: ...

    async def bulk_create(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        document_id: str,
        project_id: str,
        filename: str,
        file_type: str,
    ) -> int: ...

    async def delete_by_document(self, document_id: str) -> int: ...

    async def delete_by_project(self, project_id: str) -> int: ...


class RAGIndexingServiceProtocol(Protocol):
    """Contract for RAG document indexing."""

    async def index_document(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> IndexResult: ...

    async def reindex_document(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> IndexResult: ...

    async def delete_document_chunks(self, document_id: str) -> int: ...

    async def delete_project_chunks(self, project_id: str) -> int: ...


class RAGRetrievalServiceProtocol(Protocol):
    """Contract for RAG retrieval."""

    def embed_query(self, query: str) -> list[float]: ...

    def retrieve_chunks(
        self,
        project_id: str,
        query_embedding: list[float],
        query_text: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[dict]: ...

    def retrieve(
        self,
        project_id: str,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> RetrievalResult: ...

    def build_citations(
        self, chunks: list[dict]
    ) -> tuple[str, list[CitationInfo]]: ...


class RAGQueryServiceProtocol(Protocol):
    """Contract for query processing."""

    def rewrite_query(
        self, message: str, history: list[dict]
    ) -> str: ...
