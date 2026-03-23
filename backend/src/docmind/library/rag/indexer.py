"""RAG indexing pipeline v2.

Orchestrates: extract text → page-level chunk → embed → store.
Includes duplicate detection, contextual headers, and adaptive chunk sizing.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select

from docmind.core.config import get_settings
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import PageChunk

from .chunker import chunk_pages
from .embedder import embed_texts
from .text_extract import extract_text

logger = logging.getLogger(__name__)


async def _get_existing_hashes(project_id: str) -> set[str]:
    """Get all content hashes for chunks in a project.

    Used for duplicate detection at indexing time.

    Args:
        project_id: Project ID to scope the search.

    Returns:
        Set of content_hash strings.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(PageChunk.content_hash).where(
            PageChunk.project_id == project_id,
            PageChunk.content_hash.isnot(None),
        )
        result = await session.execute(stmt)
        rows = result.all()
        return {row[0] for row in rows if row[0]}


def _estimate_tokens(text: str) -> int:
    """Rough token estimate for embedding truncation guard.

    Conservative: ~3 chars per token for mixed English/CJK.

    Args:
        text: Input text.

    Returns:
        Estimated token count.
    """
    return len(text) // 3


async def index_document(
    document_id: str,
    project_id: str,
    file_bytes: bytes,
    file_type: str,
    filename: str = "",
) -> int:
    """Index a document for RAG: extract → chunk → dedup → embed → store.

    Pipeline:
    1. Extract text via pymupdf4llm (Markdown with headers/tables)
    2. Page-level chunking with contextual headers + adaptive sizing
    3. Duplicate detection via SHA-256 content hashes
    4. Embedding truncation guard (split if > max tokens)
    5. Embed with configured provider (DashScope/OpenAI)
    6. Store chunks + embeddings + metadata in page_chunks table

    Args:
        document_id: The document's UUID.
        project_id: The project's UUID.
        file_bytes: Raw file bytes.
        file_type: File extension/type (e.g. "pdf", "png").
        filename: Original filename for context enrichment.

    Returns:
        Number of new chunks created (excludes duplicates).
    """
    settings = get_settings()

    # 1. Extract text
    pages = extract_text(file_bytes, file_type)

    # 2. Page-level chunking with contextual headers
    doc_context = filename or document_id[:8]
    chunks = chunk_pages(
        pages,
        doc_context=doc_context,
    )

    if not chunks:
        logger.warning("No chunks extracted from document %s", document_id)
        return 0

    logger.info(
        "Chunked document %s into %d chunks (from %d pages, profile auto-detected)",
        document_id, len(chunks), len(pages),
    )

    # 3. Duplicate detection
    existing_hashes = await _get_existing_hashes(project_id)
    new_chunks = [
        c for c in chunks
        if c.get("content_hash") not in existing_hashes
    ]

    if len(new_chunks) < len(chunks):
        logger.info(
            "Skipped %d duplicate chunks for document %s",
            len(chunks) - len(new_chunks), document_id,
        )

    if not new_chunks:
        logger.info("All chunks are duplicates for document %s", document_id)
        return 0

    # 4. Embedding truncation guard
    max_tokens = settings.RAG_MAX_EMBEDDING_TOKENS
    safe_chunks: list[dict] = []
    for chunk in new_chunks:
        if _estimate_tokens(chunk["content"]) > max_tokens:
            logger.warning(
                "Chunk exceeds embedding token limit (%d est. tokens), "
                "truncating for document %s page %d",
                _estimate_tokens(chunk["content"]),
                document_id,
                chunk["page_number"],
            )
            # Truncate content to max token limit (rough: max_tokens * 3 chars)
            max_chars = max_tokens * 3
            truncated = {**chunk, "content": chunk["content"][:max_chars]}
            safe_chunks.append(truncated)
        else:
            safe_chunks.append(chunk)

    # 5. Embed (use contextualized content for better retrieval)
    texts = [c["content"] for c in safe_chunks]
    embeddings = await embed_texts(texts)

    # 6. Store with metadata
    async with AsyncSessionLocal() as session:
        for chunk_data, embedding in zip(safe_chunks, embeddings):
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
                raw_content=chunk_data.get("raw_content", ""),
                content_hash=chunk_data.get("content_hash", ""),
                embedding=json.dumps(embedding),
                metadata_json=json.dumps(metadata),
            )
            session.add(chunk)
        await session.commit()

    logger.info(
        "Indexed document %s: %d new chunks stored with embeddings",
        document_id, len(safe_chunks),
    )
    return len(safe_chunks)


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


async def reindex_document(
    document_id: str,
    project_id: str,
    file_bytes: bytes,
    file_type: str,
    filename: str = "",
) -> int:
    """Re-index a document: delete old chunks then index fresh.

    Args:
        document_id: The document's UUID.
        project_id: The project's UUID.
        file_bytes: Raw file bytes.
        file_type: File extension/type.
        filename: Original filename.

    Returns:
        Number of new chunks created.
    """
    deleted = await delete_document_chunks(document_id)
    logger.info("Deleted %d old chunks for document %s", deleted, document_id)
    return await index_document(document_id, project_id, file_bytes, file_type, filename)
