"""Project prompt service — builds prompts and formats context for RAG chat."""

# Stopword-light language heuristic — we only need to pick Indonesian vs English
# for refusal text. Covers common connectors / question words.
_INDONESIAN_MARKERS = frozenset(
    {
        "yang", "dan", "ini", "itu", "dari", "untuk", "dengan", "adalah",
        "ada", "apa", "di", "ke", "kamu", "saya", "kita", "kami", "kenapa",
        "mengapa", "siapa", "kapan", "dimana", "berapa", "bagaimana", "tidak",
        "tolong", "mohon", "jelaskan", "bagaimanakah", "berasal", "produk",
        "mana", "dokumen",
    }
)

REFUSAL_EN = (
    "I cannot find that information in the uploaded documents. "
    "Please rephrase your question or upload additional sources."
)
REFUSAL_ID = (
    "Saya tidak menemukan informasi tersebut dalam dokumen yang diunggah. "
    "Silakan coba ubah pertanyaan atau unggah dokumen tambahan."
)


def detect_language(text: str) -> str:
    """Return 'id' if the message is likely Indonesian, else 'en'.

    Deliberately simple — a stopword overlap beats nothing when the LLM would
    otherwise spend tokens guessing.
    """
    if not text:
        return "en"
    tokens = {t for t in text.lower().split() if t.isalpha()}
    if tokens & _INDONESIAN_MARKERS:
        return "id"
    return "en"


def grounded_refusal(language: str) -> str:
    """Return a refusal message in the requested language."""
    return REFUSAL_ID if language == "id" else REFUSAL_EN


class ProjectPromptService:
    """Builds prompts and formats context for project RAG chat."""

    def validate_project_name(self, name: str) -> str:
        sanitized = name.strip()
        if not sanitized:
            raise ValueError("Project name cannot be empty")
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        return sanitized

    def validate_persona_assignment(self, persona_id: str | None) -> None:
        """Validate persona can be assigned to a project."""
        if persona_id is not None and not persona_id.strip():
            raise ValueError("persona_id cannot be an empty string")

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
            "\n\nIMPORTANT — STRICT GROUNDING:"
            "\n- Base your answers ONLY on the provided context below."
            "\n- Cite every factual claim using [Source N] notation matching the"
            " context indices."
            "\n- If the context does not contain the answer, explicitly say you"
            " do not have that information in the uploaded documents — do NOT"
            " guess or rely on prior knowledge."
            "\n- When asked about files or documents, refer to the PROJECT"
            " DOCUMENTS list above."
            "\n\nMULTI-SOURCE SYNTHESIS:"
            "\n- When the question spans multiple documents or asks about an"
            " aggregate (e.g. 'where does this come from?', 'list all…', "
            "'compare…'), ENUMERATE the answer across ALL relevant sources."
            "\n- Do not stop at the first matching source — inspect every"
            " [Source N] block and report findings from each document that"
            " applies."
            "\n\nLANGUAGE: Always respond in the same language the user writes in."
            " If the user writes in Indonesian, respond in Indonesian."
            " If in English, respond in English. Match the user's language exactly."
        )
        return base

    def build_rag_context(self, chunks: list[dict]) -> tuple[str, list[dict]]:
        """Build context text and citations from retrieved chunks.

        Citations include ``chunk_id`` so the frontend can link directly to
        the exact retrieved chunk (issue #105).
        """
        context_parts: list[str] = []
        citations: list[dict] = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Source {i}]: {chunk.get('content', '')}")
            citations.append({
                "source_index": i,
                "chunk_id": chunk.get("chunk_id", ""),
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
