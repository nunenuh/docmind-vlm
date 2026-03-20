"""RAG indexing pipeline.

Orchestrates: extract text -> chunk -> embed -> store in page_chunks table.
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
) -> int:
    """Index a document for RAG: extract text, chunk, embed, store.

    Args:
        document_id: The document's UUID.
        project_id: The project's UUID.
        file_bytes: Raw file bytes.
        file_type: File extension/type (e.g. "pdf", "png").

    Returns:
        Number of chunks created.
    """
    settings = get_settings()

    # 1. Extract text
    pages = extract_text(file_bytes, file_type)

    # 2. Chunk
    chunks = chunk_pages(
        pages,
        chunk_size=settings.RAG_CHUNK_SIZE,
        overlap=settings.RAG_CHUNK_OVERLAP,
    )

    if not chunks:
        logger.warning("No chunks extracted from document %s", document_id)
        return 0

    # 3. Embed
    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)

    # 4. Store
    async with AsyncSessionLocal() as session:
        for chunk_data, embedding in zip(chunks, embeddings):
            chunk = PageChunk(
                document_id=document_id,
                project_id=project_id,
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                embedding=json.dumps(embedding),
            )
            session.add(chunk)
        await session.commit()

    logger.info("Indexed document %s: %d chunks", document_id, len(chunks))
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
