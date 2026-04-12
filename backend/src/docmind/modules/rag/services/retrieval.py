"""RAG retrieval service — query embedding and chunk retrieval via hybrid search."""

from __future__ import annotations

from docmind.core.config import Settings, get_settings
from docmind.core.logging import get_logger
from docmind.library.rag.embedder import embed_texts
from docmind.library.rag.retriever import retrieve_similar_chunks
from docmind.shared.exceptions import ProviderException, ServiceException

from ..schemas import ChunkResult, CitationInfo, RetrievalResult

logger = get_logger(__name__)


class RAGRetrievalService:
    """Query embedding and chunk retrieval via hybrid search."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def embed_query(self, query: str) -> list[float]:
        """Embed a query string. Returns embedding vector."""
        try:
            embeddings = await embed_texts([query])
            return embeddings[0]
        except Exception as e:
            logger.error("embed_query_failed: %s", e)
            raise ProviderException(f"Embedding failed: {e}") from e

    async def retrieve_chunks(
        self, project_id: str, query_embedding: list[float], query_text: str,
        top_k: int | None = None, threshold: float | None = None,
    ) -> list[dict]:
        """Retrieve relevant chunks using hybrid search (vector + BM25)."""
        try:
            return await retrieve_similar_chunks(
                query_embedding=query_embedding, project_id=project_id,
                model_name=self._settings.EMBEDDING_MODEL,
                top_k=top_k or self._settings.RAG_TOP_K,
                threshold=threshold or self._settings.RAG_SIMILARITY_THRESHOLD,
                query_text=query_text,
            )
        except Exception as e:
            logger.error("retrieve_chunks_failed: project=%s error=%s", project_id, e)
            raise ServiceException(f"Retrieval failed: {e}") from e

    async def retrieve(
        self, project_id: str, query: str,
        top_k: int | None = None, threshold: float | None = None,
    ) -> RetrievalResult:
        """Full retrieval: embed → search → return typed result."""
        embedding = await self.embed_query(query)
        chunks = await self.retrieve_chunks(
            project_id=project_id, query_embedding=embedding,
            query_text=query, top_k=top_k, threshold=threshold,
        )
        chunk_results = [
            ChunkResult(
                id=c.get("id", ""), document_id=c.get("document_id", ""),
                project_id=project_id, page_number=c.get("page_number", 0),
                chunk_index=c.get("chunk_index", 0), content=c.get("content", ""),
                raw_content=c.get("raw_content"), similarity=c.get("similarity", 0.0),
                metadata=c.get("metadata", {}),
            )
            for c in chunks
        ]
        return RetrievalResult(query=query, chunks=chunk_results, total_candidates=len(chunk_results))

    def build_citations(self, chunks: list[dict]) -> tuple[str, list[CitationInfo]]:
        """Build context text and citation info from retrieved chunks."""
        context_parts: list[str] = []
        citations: list[CitationInfo] = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Source {i}]: {chunk.get('content', '')}")
            citations.append(CitationInfo(
                source_index=i, document_id=chunk.get("document_id", ""),
                page_number=chunk.get("page_number", 0),
                content_preview=chunk.get("content", "")[:100],
                similarity=chunk.get("similarity", 0),
            ))
        context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        return context_text, citations
