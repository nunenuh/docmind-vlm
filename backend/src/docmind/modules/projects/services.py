"""
docmind/modules/projects/services.py

Project service — business logic for project operations.
Handles persona prompt building, RAG context construction, document metadata.
"""

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class ProjectService:
    """Service layer for project business logic."""

    @staticmethod
    def validate_project_name(name: str) -> str:
        """Validate and sanitize project name."""
        sanitized = name.strip()
        if not sanitized:
            raise ValueError("Project name cannot be empty")
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        return sanitized

    @staticmethod
    def validate_persona_assignment(persona_id: str | None) -> None:
        """Validate persona can be assigned to a project."""
        if persona_id is not None and not persona_id.strip():
            raise ValueError("persona_id cannot be an empty string")

    @staticmethod
    def build_system_prompt(
        persona: dict | None,
        doc_metadata: str,
        doc_count: int,
    ) -> str:
        """Build the system prompt for RAG chat with persona + document metadata.

        Args:
            persona: Persona dict with system_prompt, tone, rules, boundaries.
            doc_metadata: Formatted document list string.
            doc_count: Number of documents in project.

        Returns:
            Complete system prompt string.
        """
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

    @staticmethod
    def build_rag_context(chunks: list[dict]) -> tuple[str, list[dict]]:
        """Build context text and citations from retrieved chunks.

        Args:
            chunks: Retrieved RAG chunks.

        Returns:
            Tuple of (context_text, citations_list).
        """
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

    @staticmethod
    def format_document_metadata(docs: list) -> str:
        """Format document list for system prompt.

        Args:
            docs: List of document ORM objects.

        Returns:
            Formatted string of document names and types.
        """
        if not docs:
            return "No documents uploaded."
        return "\n".join(
            f"- {getattr(d, 'filename', 'unknown')} ({getattr(d, 'file_type', '?')}, {getattr(d, 'page_count', 0)} pages)"
            for d in docs
        )
