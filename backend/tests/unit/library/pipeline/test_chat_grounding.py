"""Tests for strict grounding in the project RAG prompt service (issue #105).

Demo-critical: system prompts must enforce single-source-of-truth behaviour.
"""

import pytest

from docmind.modules.projects.services.prompt import ProjectPromptService


@pytest.fixture
def service() -> ProjectPromptService:
    return ProjectPromptService()


class TestGroundingPrompt:
    """System prompt must enforce strict grounding and synthesis."""

    def test_prompt_demands_answers_only_from_context(self, service):
        prompt = service.build_system_prompt(
            persona=None, doc_metadata="- report.pdf", doc_count=1
        )
        assert "ONLY" in prompt
        assert (
            "context" in prompt.lower()
            and "answer" in prompt.lower()
        )

    def test_prompt_requires_explicit_refusal(self, service):
        prompt = service.build_system_prompt(
            persona=None, doc_metadata="", doc_count=0
        )
        low = prompt.lower()
        assert (
            "don't know" in low
            or "do not know" in low
            or "cannot" in low
            or "don't have" in low
            or "not contain" in low
        ), f"Prompt must explicitly instruct refusal when context lacks info: {prompt}"

    def test_prompt_requires_synthesis_across_sources(self, service):
        """When the question spans multiple docs, LLM must enumerate all of them."""
        prompt = service.build_system_prompt(
            persona=None,
            doc_metadata="- report-a.pdf\n- report-b.pdf",
            doc_count=2,
        )
        low = prompt.lower()
        assert (
            "all" in low
            and ("source" in low or "document" in low)
        ), (
            "Prompt must instruct the LLM to synthesize across all provided "
            f"sources. Got: {prompt}"
        )
        # Specifically: aggregate/enumeration directive
        assert (
            "enumerate" in low
            or "aggregate" in low
            or "multiple" in low
            or "both" in low
            or "each" in low
        ), f"Prompt must cover aggregate/multi-doc questions: {prompt}"

    def test_prompt_requires_citations(self, service):
        prompt = service.build_system_prompt(
            persona=None, doc_metadata="- doc.pdf", doc_count=1
        )
        assert "cite" in prompt.lower() or "citation" in prompt.lower() or "[Source" in prompt

    def test_prompt_language_mirroring_preserved(self, service):
        """Existing bilingual behaviour must survive the refactor."""
        prompt = service.build_system_prompt(
            persona=None, doc_metadata="- doc.pdf", doc_count=1
        )
        low = prompt.lower()
        assert "indonesian" in low or "bahasa" in low
        assert "english" in low
        assert "same language" in low or "match" in low


class TestLanguageDetectionAndRefusal:
    """Grounded refusal must respond in the user's language (issue #105)."""

    def test_detects_indonesian(self):
        from docmind.modules.projects.services.prompt import detect_language

        assert detect_language("Apa yang ada di dokumen ini?") == "id"
        assert detect_language("Produk ini berasal dari mana?") == "id"

    def test_detects_english(self):
        from docmind.modules.projects.services.prompt import detect_language

        assert detect_language("Where does this product come from?") == "en"
        assert detect_language("What is this document about?") == "en"

    def test_refusal_text_in_each_language(self):
        from docmind.modules.projects.services.prompt import grounded_refusal

        en = grounded_refusal("en")
        id_ = grounded_refusal("id")
        assert "cannot find" in en.lower() or "not find" in en.lower()
        assert "tidak menemukan" in id_.lower()


class TestBuildRagContext:
    """build_rag_context must produce citations and handle empty retrieval."""

    def test_empty_chunks_produces_empty_citations_and_sentinel_context(self, service):
        context_text, citations = service.build_rag_context([])
        assert citations == []
        assert "no relevant" in context_text.lower() or context_text.strip() == ""

    def test_citations_include_required_fields(self, service):
        chunks = [
            {
                "chunk_id": "c1",
                "document_id": "doc-A",
                "page_number": 3,
                "content": "Invoice total is $500.",
                "similarity": 0.87,
            }
        ]
        _ctx, citations = service.build_rag_context(chunks)
        assert len(citations) == 1
        cite = citations[0]
        for required in (
            "source_index",
            "document_id",
            "page_number",
            "similarity",
        ):
            assert required in cite, f"Citation missing field {required!r}: {cite}"
        # #105 ask: chunk_id must flow through so future UI can link to a chunk
        assert cite.get("chunk_id") == "c1", (
            "Citation must include chunk_id so UI can link to the exact retrieved chunk"
        )

    def test_multiple_chunks_are_indexed_and_ordered(self, service):
        chunks = [
            {"chunk_id": "c1", "document_id": "A", "page_number": 1, "content": "x", "similarity": 0.9},
            {"chunk_id": "c2", "document_id": "B", "page_number": 2, "content": "y", "similarity": 0.8},
        ]
        ctx, citations = service.build_rag_context(chunks)
        assert "[Source 1]" in ctx
        assert "[Source 2]" in ctx
        assert citations[0]["source_index"] == 1
        assert citations[1]["source_index"] == 2
