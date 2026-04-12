"""RAG indexing pipeline v2.

Orchestrates: extract text -> page-level chunk -> embed -> store.
Includes duplicate detection, contextual headers, and adaptive chunk sizing.

Embeddings are stored in chunk_embeddings table (multi-model support).
Chunks in page_chunks are immutable text — embeddings vary per model.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select

from docmind.core.config import get_settings
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import ChunkEmbedding, PageChunk

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
    provider_name: str | None = None,
    model_name: str | None = None,
    dimensions: int | None = None,
) -> int:
    """Index a document for RAG: extract -> chunk -> dedup -> embed -> store.

    Pipeline:
    1. Extract text via pymupdf4llm (Markdown with headers/tables)
    2. Page-level chunking with contextual headers + adaptive sizing
    3. Duplicate detection via SHA-256 content hashes
    4. Embedding truncation guard (split if > max tokens)
    5. Embed with configured provider (DashScope/OpenAI)
    6. Store chunks in page_chunks, embeddings in chunk_embeddings

    Args:
        document_id: The document's UUID.
        project_id: The project's UUID.
        file_bytes: Raw file bytes.
        file_type: File extension/type (e.g. "pdf", "png").
        filename: Original filename for context enrichment.
        provider_name: Embedding provider name (defaults to settings).
        model_name: Embedding model name (defaults to settings).
        dimensions: Embedding dimensions (defaults to settings).

    Returns:
        Number of new chunks created (excludes duplicates).
    """
    settings = get_settings()
    effective_provider = provider_name or settings.EMBEDDING_PROVIDER
    effective_model = model_name or settings.EMBEDDING_MODEL
    effective_dimensions = dimensions or settings.EMBEDDING_DIMENSIONS

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

    # 6. Store chunks + embeddings separately
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
                metadata_json=json.dumps(metadata),
            )
            session.add(chunk)
            await session.flush()  # Populate chunk.id for FK reference

            chunk_emb = ChunkEmbedding(
                chunk_id=chunk.id,
                document_id=document_id,
                provider_name=effective_provider,
                model_name=effective_model,
                dimensions=effective_dimensions,
                embedding=json.dumps(embedding),
            )
            session.add(chunk_emb)
        await session.commit()

    logger.info(
        "Indexed document %s: %d new chunks stored with embeddings (model=%s)",
        document_id, len(safe_chunks), effective_model,
    )
    return len(safe_chunks)


async def index_existing_chunks(
    document_id: str,
    provider_name: str | None = None,
    model_name: str | None = None,
    dimensions: int | None = None,
) -> int:
    """Embed existing chunks with a (possibly new) model. Idempotent.

    Skips chunks that already have embeddings for the specified model.

    Args:
        document_id: The document's UUID.
        provider_name: Embedding provider name (defaults to settings).
        model_name: Embedding model name (defaults to settings).
        dimensions: Embedding dimensions (defaults to settings).

    Returns:
        Number of new chunk embeddings created.
    """
    settings = get_settings()
    effective_provider = provider_name or settings.EMBEDDING_PROVIDER
    effective_model = model_name or settings.EMBEDDING_MODEL
    effective_dimensions = dimensions or settings.EMBEDDING_DIMENSIONS

    # 1. Get all chunks for this document
    async with AsyncSessionLocal() as session:
        stmt = select(PageChunk).where(PageChunk.document_id == document_id)
        result = await session.execute(stmt)
        all_chunks = result.scalars().all()

    if not all_chunks:
        logger.info("No chunks found for document %s", document_id)
        return 0

    # 2. Find chunks that already have embeddings for this model
    async with AsyncSessionLocal() as session:
        stmt = select(ChunkEmbedding.chunk_id).where(
            ChunkEmbedding.document_id == document_id,
            ChunkEmbedding.model_name == effective_model,
        )
        result = await session.execute(stmt)
        existing_chunk_ids = {row[0] for row in result.all()}

    # 3. Filter to only un-embedded chunks
    chunks_to_embed = [c for c in all_chunks if c.id not in existing_chunk_ids]

    if not chunks_to_embed:
        logger.info(
            "All chunks for document %s already have embeddings for model %s",
            document_id, effective_model,
        )
        return 0

    # 4. Embed
    texts = [c.content for c in chunks_to_embed]
    embeddings = await embed_texts(texts)

    # 5. Store embeddings
    async with AsyncSessionLocal() as session:
        for chunk, embedding in zip(chunks_to_embed, embeddings):
            chunk_emb = ChunkEmbedding(
                chunk_id=chunk.id,
                document_id=document_id,
                provider_name=effective_provider,
                model_name=effective_model,
                dimensions=effective_dimensions,
                embedding=json.dumps(embedding),
            )
            session.add(chunk_emb)
        await session.commit()

    logger.info(
        "Indexed %d chunks for document %s with model %s",
        len(chunks_to_embed), document_id, effective_model,
    )
    return len(chunks_to_embed)


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
    provider_name: str | None = None,
    model_name: str | None = None,
    dimensions: int | None = None,
) -> int:
    """Re-index a document: delete old chunks then index fresh.

    Args:
        document_id: The document's UUID.
        project_id: The project's UUID.
        file_bytes: Raw file bytes.
        file_type: File extension/type.
        filename: Original filename.
        provider_name: Embedding provider name.
        model_name: Embedding model name.
        dimensions: Embedding dimensions.

    Returns:
        Number of new chunks created.
    """
    deleted = await delete_document_chunks(document_id)
    logger.info("Deleted %d old chunks for document %s", deleted, document_id)
    return await index_document(
        document_id, project_id, file_bytes, file_type, filename,
        provider_name, model_name, dimensions,
    )
