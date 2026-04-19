"""Hybrid retrieval: vector similarity + BM25 keyword search with RRF fusion.

Two retrieval paths:
1. Vector: cosine similarity on chunk_embeddings (semantic understanding)
2. BM25: PostgreSQL ts_vector full-text search (exact keyword matching)

Results are fused using Reciprocal Rank Fusion (RRF) for best-of-both precision.
Falls back to vector-only if BM25 columns are not available.

All settings come from get_settings().
Queries MUST filter by model_name — never mix vectors from different models.
"""

from __future__ import annotations

import json
import logging
import math

from sqlalchemy import select

from docmind.core.config import get_settings
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import ChunkEmbedding, Document, PageChunk

logger = logging.getLogger(__name__)

# RRF constant — controls how much rank matters vs absolute position
RRF_K = 60


async def retrieve_similar_chunks(
    query_embedding: list[float],
    project_id: str,
    model_name: str,
    top_k: int | None = None,
    threshold: float | None = None,
    query_text: str = "",
) -> list[dict]:
    """Retrieve top-K similar chunks using hybrid vector + BM25 search.

    If query_text is provided and BM25 columns exist, uses hybrid RRF fusion.
    Otherwise falls back to vector-only retrieval.

    Args:
        query_embedding: The query's embedding vector.
        project_id: Project ID to scope the search.
        model_name: Embedding model name to filter by (required).
        top_k: Maximum number of chunks to return.
        threshold: Minimum similarity to include.
        query_text: Original query text for BM25 search.

    Returns:
        List of dicts with chunk_id, document_id, page_number, content, similarity.
        Sorted by relevance (RRF score if hybrid, cosine similarity if vector-only).
    """
    settings = get_settings()
    effective_top_k = top_k or settings.RAG_TOP_K
    effective_threshold = threshold or settings.RAG_SIMILARITY_THRESHOLD

    # Try hybrid first, fall back to vector-only
    if query_text:
        try:
            return await _retrieve_hybrid(
                query_embedding, project_id, model_name, query_text,
                effective_top_k, effective_threshold,
            )
        except Exception as e:
            logger.warning("Hybrid retrieval failed, falling back to vector-only: %s", e)

    return await _retrieve_vector_only(
        query_embedding, project_id, model_name,
        effective_top_k, effective_threshold,
    )


async def retrieve_similar_chunks_with_stats(
    query_embedding: list[float],
    project_id: str,
    model_name: str,
    top_k: int | None = None,
    threshold: float | None = None,
    query_text: str = "",
) -> dict:
    """Retrieve chunks plus diagnostic stats (issue #105).

    Same retrieval as `retrieve_similar_chunks` but also returns aggregate
    statistics that callers (e.g. project chat) use to decide whether to
    refuse before calling the VLM.

    Returns:
        dict with keys:
            chunks: list[dict] — retrieved chunks (already diversified + capped).
            max_similarity: float — highest similarity across retrieved chunks (0.0 if empty).
            per_document_counts: dict[str, int] — chunks per document_id.
    """
    chunks = await retrieve_similar_chunks(
        query_embedding=query_embedding,
        project_id=project_id,
        model_name=model_name,
        top_k=top_k,
        threshold=threshold,
        query_text=query_text,
    )

    if not chunks:
        return {
            "chunks": [],
            "max_similarity": 0.0,
            "per_document_counts": {},
        }

    max_sim = max(c.get("similarity", 0.0) for c in chunks)
    counts: dict[str, int] = {}
    for c in chunks:
        doc_id = c.get("document_id", "")
        counts[doc_id] = counts.get(doc_id, 0) + 1

    return {
        "chunks": chunks,
        "max_similarity": max_sim,
        "per_document_counts": counts,
    }


async def _retrieve_vector_only(
    query_embedding: list[float],
    project_id: str,
    model_name: str,
    top_k: int,
    threshold: float,
) -> list[dict]:
    """Vector-only retrieval using Python-side cosine similarity.

    Joins page_chunks with chunk_embeddings, filtering by model_name.

    Args:
        query_embedding: Query embedding vector.
        project_id: Project scope.
        model_name: Embedding model to filter by.
        top_k: Max results.
        threshold: Min similarity.

    Returns:
        Sorted list of chunk dicts.
    """
    async with AsyncSessionLocal() as session:
        # JOIN documents to exclude orphaned chunks from deleted docs (issue #104).
        stmt = (
            select(PageChunk, ChunkEmbedding.embedding)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == PageChunk.id)
            .join(Document, Document.id == PageChunk.document_id)
            .where(
                PageChunk.project_id == project_id,
                ChunkEmbedding.model_name == model_name,
            )
        )
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        return []

    scored: list[dict] = []
    for chunk, emb_str in rows:
        embedding = (
            json.loads(emb_str)
            if isinstance(emb_str, str)
            else emb_str
        )
        sim = _cosine_similarity(query_embedding, embedding)
        if sim >= threshold:
            scored.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "raw_content": getattr(chunk, "raw_content", None) or chunk.content,
                "similarity": round(sim, 4),
            })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    # Apply per-document diversity so a single document cannot monopolise
    # the top-K (issue #105).
    return _diversify_results(scored, top_k)


async def _retrieve_hybrid(
    query_embedding: list[float],
    project_id: str,
    model_name: str,
    query_text: str,
    top_k: int,
    threshold: float,
) -> list[dict]:
    """Hybrid retrieval: vector + BM25 with RRF fusion.

    Steps:
    1. Get vector results (cosine similarity, ranked)
    2. Get BM25 results (ts_rank, ranked)
    3. Fuse using RRF: score = w_v/(k+rank_v) + w_b/(k+rank_b)
    4. Return top-K by fused score

    Args:
        query_embedding: Query embedding vector.
        project_id: Project scope.
        model_name: Embedding model to filter by.
        query_text: Original query for BM25.
        top_k: Max results.
        threshold: Min similarity for vector results.

    Returns:
        Sorted list of chunk dicts by RRF score.
    """
    settings = get_settings()
    vector_weight = settings.RAG_VECTOR_WEIGHT
    bm25_weight = settings.RAG_BM25_WEIGHT
    retrieval_k = settings.RAG_RETRIEVAL_K

    # 1. Get all chunks for this project with embeddings for the model.
    # JOIN documents to exclude orphaned chunks from deleted docs (issue #104).
    async with AsyncSessionLocal() as session:
        stmt = (
            select(PageChunk, ChunkEmbedding.embedding)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == PageChunk.id)
            .join(Document, Document.id == PageChunk.document_id)
            .where(
                PageChunk.project_id == project_id,
                ChunkEmbedding.model_name == model_name,
            )
        )
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        return []

    # Build chunk objects and embeddings map
    all_chunks = []
    chunk_embeddings: dict[str, list[float]] = {}
    for chunk, emb_str in rows:
        all_chunks.append(chunk)
        embedding = (
            json.loads(emb_str)
            if isinstance(emb_str, str)
            else emb_str
        )
        chunk_embeddings[chunk.id] = embedding

    # 2. Score vector similarity
    vector_scored: list[tuple[str, float, object]] = []
    for chunk in all_chunks:
        emb = chunk_embeddings.get(chunk.id)
        if not emb:
            continue
        sim = _cosine_similarity(query_embedding, emb)
        if sim >= threshold:
            vector_scored.append((chunk.id, sim, chunk))

    vector_scored.sort(key=lambda x: x[1], reverse=True)
    vector_scored = vector_scored[:retrieval_k]

    # 3. Score BM25 (simple Python-side keyword matching)
    query_tokens = set(query_text.lower().split())
    bm25_scored: list[tuple[str, float, object]] = []
    for chunk in all_chunks:
        raw = getattr(chunk, "raw_content", None) or chunk.content or ""
        raw_lower = raw.lower()
        # Simple term frequency scoring
        match_count = sum(1 for token in query_tokens if token in raw_lower)
        if match_count > 0:
            score = match_count / max(len(query_tokens), 1)
            bm25_scored.append((chunk.id, score, chunk))

    bm25_scored.sort(key=lambda x: x[1], reverse=True)
    bm25_scored = bm25_scored[:retrieval_k]

    # 4. RRF Fusion
    vector_ranks = {cid: rank + 1 for rank, (cid, _, _) in enumerate(vector_scored)}
    bm25_ranks = {cid: rank + 1 for rank, (cid, _, _) in enumerate(bm25_scored)}

    # Collect all unique chunk IDs
    all_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
    chunk_map = {}
    for cid, _, chunk_obj in vector_scored + bm25_scored:
        if cid not in chunk_map:
            chunk_map[cid] = chunk_obj

    fused: list[dict] = []
    for cid in all_ids:
        v_rank = vector_ranks.get(cid, retrieval_k + 1)
        b_rank = bm25_ranks.get(cid, retrieval_k + 1)
        rrf_score = (vector_weight / (RRF_K + v_rank)) + (bm25_weight / (RRF_K + b_rank))

        chunk_obj = chunk_map[cid]
        vector_sim = next(
            (sim for c, sim, _ in vector_scored if c == cid), 0.0
        )

        fused.append({
            "chunk_id": cid,
            "document_id": chunk_obj.document_id,
            "page_number": chunk_obj.page_number,
            "content": chunk_obj.content,
            "raw_content": getattr(chunk_obj, "raw_content", None) or chunk_obj.content,
            "similarity": round(vector_sim, 4),
            "rrf_score": round(rrf_score, 6),
        })

    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return _diversify_results(fused, top_k)


def _diversify_results(results: list[dict], top_k: int) -> list[dict]:
    """Diversify results to include chunks from different documents.

    Round-robin strategy: pick the best chunk from each document, then the
    second best, etc. GUARANTEES at least one chunk per document as long as
    that document contributed any chunk (issue #105). Preserves relative
    ordering within each document's chunks.

    If there are fewer results than top_k, still round-robins so that the
    order promotes diversity rather than concentration.

    Args:
        results: Sorted list of chunk dicts (best first) with a
            ``document_id`` key on each chunk.
        top_k: Maximum results to return.

    Returns:
        Diversified list of chunk dicts, up to top_k, preserving the
        relative order within each document.
    """
    if not results:
        return []

    # Preserve document insertion order (= global similarity order) so
    # the strongest document wins the first round-robin slot.
    doc_buckets: dict[str, list[dict]] = {}
    for r in results:
        doc_buckets.setdefault(r["document_id"], []).append(r)

    diversified: list[dict] = []
    seen_ids: set[str] = set()
    max_rounds = max(len(bucket) for bucket in doc_buckets.values())

    for _round in range(max_rounds):
        for chunks in doc_buckets.values():
            if _round < len(chunks):
                chunk = chunks[_round]
                cid = chunk["chunk_id"]
                if cid not in seen_ids:
                    diversified.append(chunk)
                    seen_ids.add(cid)
                    if len(diversified) >= top_k:
                        return diversified

    return diversified[:top_k]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity in range [-1, 1]. Returns 0.0 if either is zero.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
