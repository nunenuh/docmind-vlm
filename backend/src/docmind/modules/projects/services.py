"""
docmind/modules/projects/services.py

Project services — multiple focused service classes.
Usecase delegates all library/API calls here.
"""

from typing import AsyncGenerator

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.library.providers.factory import get_vlm_provider
from docmind.library.rag.embedder import embed_texts
from docmind.library.rag.indexer import index_document, reindex_document
from docmind.library.rag.query_rewriter import rewrite_query_with_context
from docmind.library.rag.retriever import retrieve_similar_chunks

logger = get_logger(__name__)


class ProjectPromptService:
    """Builds prompts and formats context for project RAG chat."""

    def validate_project_name(self, name: str) -> str:
        sanitized = name.strip()
        if not sanitized:
            raise ValueError("Project name cannot be empty")
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        return sanitized

    def build_system_prompt(
        self,
        persona: dict | None,
        doc_metadata: str,
        doc_count: int,
    ) -> str:
        """Build system prompt with persona + document metadata."""
        base = (
            persona["system_prompt"]
            if persona and persona.get("system_prompt")
            else "You are a helpful document assistant. Answer based ONLY on the provided context."
        )
        if persona and persona.get("tone"):
            base += f"\n\nTone: {persona['tone']}"
        if persona and persona.get("rules"):
            base += f"\n\nRules: {persona['rules']}"
        if persona and persona.get("boundaries"):
            base += f"\n\nBoundaries: {persona['boundaries']}"

        base += (
            f"\n\nPROJECT DOCUMENTS ({doc_count} files):\n{doc_metadata}"
            "\n\nIMPORTANT: Base your answers ONLY on the provided context. "
            "Cite sources using [Source N] notation. "
            "If the context doesn't contain relevant information, say so clearly. "
            "When asked about files or documents, refer to the PROJECT DOCUMENTS list above."
        )
        return base

    def build_rag_context(self, chunks: list[dict]) -> tuple[str, list[dict]]:
        """Build context text and citations from retrieved chunks."""
        context_parts: list[str] = []
        citations: list[dict] = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Source {i}]: {chunk.get('content', '')}")
            citations.append({
                "source_index": i,
                "document_id": chunk.get("document_id", ""),
                "page_number": chunk.get("page_number", 0),
                "content_preview": chunk.get("content", "")[:100],
                "similarity": chunk.get("similarity", 0),
            })
        context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        return context_text, citations

    def format_document_metadata(self, docs: list) -> str:
        """Format document list for system prompt."""
        if not docs:
            return "No documents uploaded."
        return "\n".join(
            f"- {getattr(d, 'filename', 'unknown')} ({getattr(d, 'file_type', '?')}, {getattr(d, 'page_count', 0)} pages)"
            for d in docs
        )


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


class ProjectIndexingService:
    """Document indexing for RAG."""

    async def index(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> int:
        """Index a document: extract text → chunk → embed → store."""
        return await index_document(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=file_type,
            filename=filename,
        )

    async def reindex(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> int:
        """Re-index: delete old chunks → re-extract → re-embed."""
        return await reindex_document(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=file_type,
            filename=filename,
        )


class ProjectVLMService:
    """VLM streaming for project chat."""

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()

    async def stream_chat(
        self,
        message: str,
        system_prompt: str,
        history: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """Stream VLM response with thinking."""
        provider = get_vlm_provider()
        async for event in provider.chat_stream(
            images=[],
            message=message,
            history=history[-6:],
            system_prompt=system_prompt,
            enable_thinking=self._settings.ENABLE_THINKING,
        ):
            yield event
