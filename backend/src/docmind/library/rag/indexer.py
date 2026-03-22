"""RAG indexing pipeline.

Orchestrates: extract text (pymupdf4llm) → header-aware chunk → embed → store.
Each chunk is enriched with section context for self-contained retrieval.
"""

from __future__ import annotations

import json
import logging

from docmind.core.config import get_settings
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import PageChunk

from .chunker import chunk_pages
from .embedder import embed_texts
from .text_extract import extract_text

logger = logging.getLogger(__name__)


async def index_document(
    document_id: str,
    project_id: str,
    file_bytes: bytes,
    file_type: str,
    filename: str = "",
) -> int:
    """Index a document for RAG: extract text, chunk, embed, store.

    Pipeline:
    1. Extract text via pymupdf4llm (Markdown with headers/tables)
    2. Split by headers first, then recursive sentence split
    3. Contextualize each chunk with section header + doc name
    4. Embed with configured provider (DashScope/OpenAI)
    5. Store chunks + embeddings + metadata in page_chunks table

    Args:
        document_id: The document's UUID.
        project_id: The project's UUID.
        file_bytes: Raw file bytes.
        file_type: File extension/type (e.g. "pdf", "png").
        filename: Original filename for context enrichment.

    Returns:
        Number of chunks created.
    """
    settings = get_settings()

    # 1. Extract text (pymupdf4llm for PDFs, fallback for images)
    pages = extract_text(file_bytes, file_type)

    # 2. Header-aware chunking with contextual enrichment
    doc_context = filename or document_id[:8]
    chunks = chunk_pages(
        pages,
        chunk_size=settings.RAG_CHUNK_SIZE,
        overlap=settings.RAG_CHUNK_OVERLAP,
        doc_context=doc_context,
    )

    if not chunks:
        logger.warning("No chunks extracted from document %s", document_id)
        return 0

    logger.info(
        "Chunked document %s into %d chunks (from %d pages)",
        document_id, len(chunks), len(pages),
    )

    # 3. Embed (use contextualized content for better retrieval)
    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)

    # 4. Store with metadata
    async with AsyncSessionLocal() as session:
        for chunk_data, embedding in zip(chunks, embeddings):
            metadata = {
                "section_header": chunk_data.get("section_header", ""),
                "filename": filename,
                "file_type": file_type,
            }
            chunk = PageChunk(
                document_id=document_id,
                project_id=project_id,
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                embedding=json.dumps(embedding),
                metadata_json=json.dumps(metadata),
            )
            session.add(chunk)
        await session.commit()

    logger.info(
        "Indexed document %s: %d chunks stored with embeddings",
        document_id, len(chunks),
    )
    return len(chunks)


async def delete_document_chunks(document_id: str) -> int:
    """Delete all chunks for a document.

    Args:
        document_id: The document's UUID.

    Returns:
        Number of chunks deleted.
    """
    from sqlalchemy import delete as sa_delete

    async with AsyncSessionLocal() as session:
        stmt = sa_delete(PageChunk).where(PageChunk.document_id == document_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount
