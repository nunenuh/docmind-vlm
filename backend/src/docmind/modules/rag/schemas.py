"""
docmind/modules/rag/schemas.py

Pydantic schemas for RAG module — internal DTOs and API request/response models.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChunkResult(BaseModel):
    """Single chunk returned from retrieval or listing."""

    id: str
    document_id: str
    project_id: str
    page_number: int
    chunk_index: int
    content: str
    raw_content: str | None = None
    content_hash: str | None = None
    similarity: float = 0.0
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class RetrievalResult(BaseModel):
    """Result of a RAG retrieval operation."""

    query: str
    rewritten_query: str | None = None
    chunks: list[ChunkResult]
    total_candidates: int = 0


class IndexResult(BaseModel):
    """Result of a document indexing operation."""

    document_id: str
    project_id: str
    chunks_created: int
    duplicates_skipped: int = 0


class ChunkListResult(BaseModel):
    """Paginated list of chunks for browsing."""

    chunks: list[ChunkResult]
    total: int


class CitationInfo(BaseModel):
    """Citation reference for a retrieved chunk."""

    source_index: int
    document_id: str
    page_number: int
    content_preview: str
    similarity: float = 0.0


# ── API Request / Response Schemas ────────────────────────


class RAGSearchRequest(BaseModel):
    """Request body for semantic search."""

    project_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1, max_length=10000)
    history: list[dict] | None = Field(
        default=None,
        description="Conversation history for query rewriting: [{role, content}]",
    )
    top_k: int | None = Field(default=None, ge=1, le=50)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class RAGStatsResponse(BaseModel):
    """Chunk statistics for a project."""

    project_id: str
    total_chunks: int
    document_chunks: dict[str, int] = Field(
        default_factory=dict,
        description="Chunk count per document_id",
    )
