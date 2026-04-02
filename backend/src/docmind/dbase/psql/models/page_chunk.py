"""PageChunk Model.

Stores chunked document text with embeddings for RAG retrieval.
All queries MUST filter by project_id.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PageChunk(Base):
    __tablename__ = "page_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Original text without contextual header (for BM25)
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hash for duplicate detection
    embedding: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Stored as pgvector-compatible string '[0.1,0.2,...]'; DB column is vector(1024)
    metadata_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string for extra metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
