"""Project RAG service — embedding, retrieval, query rewriting."""

from docmind.core.config import get_settings
from docmind.library.rag.embedder import embed_texts
from docmind.library.rag.query_rewriter import rewrite_query_with_context
from docmind.library.rag.retriever import retrieve_similar_chunks


class ProjectRAGService:
    """RAG operations: embedding, retrieval, query rewriting."""

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()

    async def embed_query(self, query: str) -> list[float]:
        """Embed a query string. Returns embedding vector."""
        embeddings = await embed_texts([query])
        return embeddings[0]

    async def retrieve_chunks(
        self,
        project_id: str,
        query_embedding: list[float],
        query_text: str,
    ) -> list[dict]:
        """Retrieve relevant chunks using hybrid search."""
        return await retrieve_similar_chunks(
            query_embedding=query_embedding,
            project_id=project_id,
            top_k=self._settings.RAG_TOP_K,
            threshold=self._settings.RAG_SIMILARITY_THRESHOLD,
            query_text=query_text,
        )

    async def rewrite_query(self, message: str, history: list[dict]) -> str:
        """Rewrite query with conversation context."""
        return await rewrite_query_with_context(message, history)
