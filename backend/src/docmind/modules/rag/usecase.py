"""
docmind/modules/rag/usecase.py

RAG use case — orchestrates indexing, retrieval, and query services.
This is the primary entry point for any module that needs RAG capabilities.
NEVER calls library directly — delegates all work to services + repository.
"""

from __future__ import annotations

from docmind.core.logging import get_logger
from docmind.shared.exceptions import (
    IndexingException,
    NotFoundException,
    ValidationException,
)

from .repositories import ChunkRepository
from .schemas import (
    ChunkListResult,
    ChunkResult,
    CitationInfo,
    IndexResult,
    RetrievalResult,
)
from .services import RAGIndexingService, RAGQueryService, RAGRetrievalService

logger = get_logger(__name__)


class RAGUseCase:
    """Orchestrates RAG operations. Any module can use this.

    Provides high-level methods that combine multiple service calls
    into cohesive workflows.

    Example usage from another module:
        rag = RAGUseCase()
        result = await rag.retrieve_with_rewrite(
            project_id="...",
            query="What about his education?",
            history=[{"role": "user", "content": "Tell me about Bima Jaya"}],
        )
        context_text, citations = rag.build_context(result.chunks)
    """

    def __init__(
        self,
        chunk_repo: ChunkRepository | None = None,
        indexing_service: RAGIndexingService | None = None,
        retrieval_service: RAGRetrievalService | None = None,
        query_service: RAGQueryService | None = None,
    ) -> None:
        self._chunk_repo = chunk_repo or ChunkRepository()
        self._indexing_service = indexing_service or RAGIndexingService(
            chunk_repo=self._chunk_repo,
        )
        self._retrieval_service = retrieval_service or RAGRetrievalService()
        self._query_service = query_service or RAGQueryService()

    # ── Indexing ──────────────────────────────────────────

    async def index_document(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str = "",
    ) -> IndexResult:
        """Index a document for RAG: extract → chunk → dedup → embed → store.

        Args:
            document_id: Document UUID.
            project_id: Project UUID.
            file_bytes: Raw file content.
            file_type: File extension (e.g. "pdf").
            filename: Original filename for contextual headers.

        Returns:
            IndexResult with chunk counts.

        Raises:
            ValidationException: If input is invalid.
            IndexingException: On pipeline failure.
        """
        if not file_bytes:
            raise ValidationException("File content is empty")
        if not document_id or not project_id:
            raise ValidationException("document_id and project_id are required")

        return await self._indexing_service.index_document(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=file_type,
            filename=filename,
        )

    async def reindex_document(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str = "",
    ) -> IndexResult:
        """Re-index: delete old chunks → index fresh.

        Returns:
            IndexResult with new chunk counts.
        """
        if not file_bytes:
            raise ValidationException("File content is empty")

        return await self._indexing_service.reindex_document(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=file_type,
            filename=filename,
        )

    async def delete_document_chunks(self, document_id: str) -> int:
        """Delete all RAG chunks for a document.

        Returns:
            Number of chunks deleted.
        """
        return await self._indexing_service.delete_document_chunks(document_id)

    async def delete_project_chunks(self, project_id: str) -> int:
        """Delete all RAG chunks for a project.

        Returns:
            Number of chunks deleted.
        """
        return await self._indexing_service.delete_project_chunks(project_id)

    # ── Retrieval ─────────────────────────────────────────

    async def retrieve(
        self,
        project_id: str,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> RetrievalResult:
        """Embed query and retrieve relevant chunks.

        Simple retrieval without query rewriting.

        Args:
            project_id: Project scope.
            query: Search query.
            top_k: Override default RAG_TOP_K.
            threshold: Override default similarity threshold.

        Returns:
            RetrievalResult with ranked chunks.
        """
        return await self._retrieval_service.retrieve(
            project_id=project_id,
            query=query,
            top_k=top_k,
            threshold=threshold,
        )

    async def retrieve_with_rewrite(
        self,
        project_id: str,
        query: str,
        history: list[dict] | None = None,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> RetrievalResult:
        """Full retrieval pipeline: rewrite → embed → search.

        Handles ambiguous follow-up questions by rewriting them
        with conversation context before retrieval.

        Args:
            project_id: Project scope.
            query: User's message.
            history: Conversation history [{"role": ..., "content": ...}].
            top_k: Override default RAG_TOP_K.
            threshold: Override default similarity threshold.

        Returns:
            RetrievalResult with rewritten_query and ranked chunks.
        """
        # 1. Query rewriting
        search_query = query
        if history:
            search_query = await self._query_service.rewrite_query(query, history)

        # 2. Embed + retrieve
        result = await self._retrieval_service.retrieve(
            project_id=project_id,
            query=search_query,
            top_k=top_k,
            threshold=threshold,
        )

        # 3. Annotate with rewrite info
        if search_query != query:
            result.rewritten_query = search_query

        return result

    def build_context(
        self, chunks: list[ChunkResult] | list[dict]
    ) -> tuple[str, list[CitationInfo]]:
        """Build context string and citation list from retrieved chunks.

        Convenience wrapper around RAGRetrievalService.build_citations.
        Accepts either ChunkResult objects or raw dicts.

        Args:
            chunks: Retrieved chunks (ChunkResult or dict).

        Returns:
            Tuple of (context_text, citations).
        """
        chunk_dicts = [
            c.model_dump() if isinstance(c, ChunkResult) else c
            for c in chunks
        ]
        return self._retrieval_service.build_citations(chunk_dicts)

    # ── Chunk Browsing ────────────────────────────────────

    async def list_chunks(
        self,
        project_id: str,
        document_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ChunkListResult:
        """List RAG chunks for browsing/inspection.

        Args:
            project_id: Project scope.
            document_id: Optional document filter.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            ChunkListResult with chunks and total count.
        """
        chunks, total = await self._chunk_repo.list_by_project(
            project_id=project_id,
            document_id=document_id,
            limit=limit,
            offset=offset,
        )

        return ChunkListResult(
            chunks=[
                ChunkResult(
                    id=c.id,
                    document_id=c.document_id,
                    project_id=c.project_id,
                    page_number=c.page_number,
                    chunk_index=c.chunk_index,
                    content=c.content[:200] + "..." if len(c.content or "") > 200 else c.content,
                    raw_content=(c.raw_content or "")[:200] + "..." if len(c.raw_content or "") > 200 else c.raw_content,
                    content_hash=c.content_hash,
                    created_at=c.created_at,
                )
                for c in chunks
            ],
            total=total,
        )

    async def get_chunk(self, chunk_id: str, project_id: str) -> ChunkResult:
        """Get a single chunk by ID with full content.

        Raises:
            NotFoundException: If chunk not found.
        """
        try:
            chunk = await self._chunk_repo.get_by_id(chunk_id, project_id)
        except Exception:
            raise NotFoundException(f"Chunk {chunk_id} not found")

        return ChunkResult(
            id=chunk.id,
            document_id=chunk.document_id,
            project_id=chunk.project_id,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            raw_content=chunk.raw_content,
            content_hash=chunk.content_hash,
            created_at=chunk.created_at,
        )

    async def get_chunk_count(self, project_id: str) -> int:
        """Get total chunk count for a project."""
        return await self._chunk_repo.count_by_project(project_id)

    async def get_document_chunk_count(self, document_id: str) -> int:
        """Get total chunk count for a document."""
        return await self._chunk_repo.count_by_document(document_id)
