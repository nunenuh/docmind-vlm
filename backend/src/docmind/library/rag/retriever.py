"""Chunk retrieval with cosine similarity.

Retrieves the most relevant chunks for a query from a project's indexed documents.
Currently uses Python-side cosine similarity; will be replaced with pgvector <=>
operator when migrations are set up.
"""

from __future__ import annotations

import json
import math

from sqlalchemy import select

from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import PageChunk


async def retrieve_similar_chunks(
    query_embedding: list[float],
    project_id: str,
    top_k: int = 5,
    threshold: float = 0.7,
) -> list[dict]:
    """Retrieve top-K similar chunks for a project using cosine similarity.

    For now (without pgvector), uses Python-side cosine similarity.
    Will be replaced with pgvector <=> operator when migrations are set up.

    Args:
        query_embedding: The query's embedding vector.
        project_id: Project ID to scope the search.
        top_k: Maximum number of chunks to return.
        threshold: Minimum cosine similarity to include a chunk.

    Returns:
        List of dicts with chunk_id, document_id, page_number, content, similarity.
        Sorted by similarity descending.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(PageChunk).where(PageChunk.project_id == project_id)
        result = await session.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        scored: list[dict] = []
        for chunk in chunks:
            if chunk.embedding:
                embedding = (
                    json.loads(chunk.embedding)
                    if isinstance(chunk.embedding, str)
                    else chunk.embedding
                )
                sim = _cosine_similarity(query_embedding, embedding)
                if sim >= threshold:
                    scored.append(
                        {
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "page_number": chunk.page_number,
                            "content": chunk.content,
                            "similarity": sim,
                        }
                    )

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity in range [-1, 1]. Returns 0.0 if either vector is zero.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
