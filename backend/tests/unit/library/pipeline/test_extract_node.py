"""
Unit tests for the extract_node pipeline function (general mode).

VLM provider is fully mocked. Tests verify field extraction,
confidence handling, document classification fallback,
audit entries, error handling, and malformed response handling.
"""
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import numpy as np
import pytest


def _make_fake_provider(
    extract_response: dict | None = None,
    classify_response: dict | None = None,
    provider_name: str = "test-provider",
    model_name: str = "test-model",
):
    """Create a mock VLM provider with configurable responses."""
    provider = MagicMock()
    type(provider).provider_name = PropertyMock(return_value=provider_name)
    type(provider).model_name = PropertyMock(return_value=model_name)

    if extract_response is None:
        # Default: summarize-style response (no template mode)
        extract_response = {
            "content": "Summarized content",
            "structured_data": {
                "document_type": "invoice",
                "summary": "An invoice from Acme Corp for $500.",
                "language": "English",
                "sections": [
                    {"name": "Header", "content_preview": "Invoice INV-001", "page_number": 1},
                ],
                "entities": [
                    {"type": "org", "value": "Acme Corp", "page_number": 1},
                    {"type": "date", "value": "2026-01-15", "page_number": 1},
                ],
            },
            "confidence": 0.9,
            "model": "test-model",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "raw_response": {},
        }

    if classify_response is None:
        classify_response = {
            "content": "invoice",
            "structured_data": {"document_type": "invoice"},
            "confidence": 0.85,
            "model": "test-model",
            "usage": {"prompt_tokens": 50, "completion_tokens": 10},
            "raw_response": {},
        }

    provider.extract = AsyncMock(return_value=extract_response)
    provider.classify = AsyncMock(return_value=classify_response)
    return provider


def _make_state(
    page_images: list | None = None,
    template_type: str | None = None,
    callback: object | None = None,
) -> dict:
    """Build a minimal ProcessingState for extract_node."""
    if page_images is None:
        page_images = [np.zeros((100, 100, 3), dtype=np.uint8)]
    return {
        "document_id": "doc-123",
        "user_id": "user-456",
        "file_bytes": b"",
        "file_type": "pdf",
        "template_type": template_type,
        "page_images": page_images,
        "page_count": len(page_images),
        "quality_map": {},
        "skew_angles": [],
        "raw_fields": [],
        "vlm_response": {},
        "document_type": None,
        "enhanced_fields": [],
        "comparison_data": {},
        "extraction_id": "",
        "status": "processing",
        "error_message": None,
        "audit_entries": [],
        "progress_callback": callback,
    }


class TestExtractNodeGeneralMode:
    """Tests for general (schema-free) extraction."""

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_extracts_summary_fields_from_vlm_response(self, mock_get_provider):
        """extract_node returns raw_fields from summarize response."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        # Should have summary fields (document_type, summary, language) + 1 section + 2 entities = 6
        assert len(result["raw_fields"]) == 6
        field_keys = [f["field_key"] for f in result["raw_fields"]]
        assert "document_type" in field_keys
        assert "summary" in field_keys

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_attaches_vlm_confidence_to_summary_fields(self, mock_get_provider):
        """Summary fields get vlm_confidence from the response-level confidence."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        for field in result["raw_fields"]:
            assert field["vlm_confidence"] == 0.9

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_does_not_mutate_original_vlm_response(self, mock_get_provider):
        """Original structured_data from VLM response must not be mutated."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider
        original_sections = provider.extract.return_value["structured_data"]["sections"]

        state = _make_state()
        extract_node(state)

        # Original sections should not have vlm_confidence added
        assert "vlm_confidence" not in original_sections[0]

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_vlm_confidence_falls_back_to_response_level(self, mock_get_provider):
        """If field has no confidence, use VLM response-level confidence."""
        from docmind.library.pipeline.extraction.extract import extract_node

        response = {
            "content": "text",
            "structured_data": {
                "fields": [
                    {"field_type": "text_block", "field_key": None, "field_value": "Hello", "page_number": 1, "bounding_box": {}},
                ],
                "document_type": "letter",
            },
            "confidence": 0.7,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert result["raw_fields"][0]["vlm_confidence"] == 0.7

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_returns_document_type_from_vlm(self, mock_get_provider):
        """document_type is extracted from VLM response structured_data."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert result["document_type"] == "invoice"

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_classifies_when_no_document_type_detected(self, mock_get_provider):
        """If general mode and no document_type in response, calls classify()."""
        from docmind.library.pipeline.extraction.extract import extract_node

        response = {
            "content": "text",
            "structured_data": {"fields": [], "document_type": None},
            "confidence": 0.5,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        classify_resp = {
            "content": "receipt",
            "structured_data": {"document_type": "receipt"},
            "confidence": 0.8,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response, classify_response=classify_resp)
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        provider.classify.assert_called_once()
        assert result["document_type"] == "receipt"

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_skips_classify_when_document_type_present(self, mock_get_provider):
        """If document_type is already in response, don't call classify()."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        extract_node(state)

        provider.classify.assert_not_called()

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_serializes_vlm_response(self, mock_get_provider):
        """vlm_response in result contains content, confidence, model, usage."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        vlm = result["vlm_response"]
        assert "content" in vlm
        assert "confidence" in vlm
        assert "model" in vlm
        assert "usage" in vlm

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_creates_audit_entry(self, mock_get_provider):
        """extract_node appends audit entry with step_name='extract'."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert len(result["audit_entries"]) == 1
        entry = result["audit_entries"][0]
        assert entry["step_name"] == "extract"
        assert entry["step_order"] == 2
        assert entry["input_summary"]["mode"] == "summarize"
        assert entry["output_summary"]["field_count"] == 6
        assert entry["output_summary"]["vlm_model"] == "test-model"
        assert entry["parameters"]["provider"] == "test-provider"
        assert entry["parameters"]["model"] == "test-model"
        assert isinstance(entry["duration_ms"], int)


class TestExtractNodeCallbackAndErrors:
    """Tests for callback invocation and error handling."""

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_callback_invoked_at_substeps(self, mock_get_provider):
        """progress_callback is called multiple times during extraction."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider
        callback = MagicMock()

        state = _make_state(callback=callback)
        extract_node(state)

        assert callback.call_count >= 3

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_works_without_callback(self, mock_get_provider):
        """extract_node works when callback is None."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(callback=None)
        result = extract_node(state)

        assert len(result["raw_fields"]) > 0

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_returns_error_on_provider_failure(self, mock_get_provider):
        """If VLM provider raises, returns status='error'."""
        from docmind.library.pipeline.extraction.extract import extract_node

        provider = _make_fake_provider()
        provider.extract = AsyncMock(side_effect=RuntimeError("VLM API timeout"))
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert result["status"] == "error"
        assert result["error_message"] == "Extraction failed. See server logs for details."

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_handles_malformed_vlm_response_missing_fields(self, mock_get_provider):
        """If VLM response has no 'fields' key, treats as empty list."""
        from docmind.library.pipeline.extraction.extract import extract_node

        response = {
            "content": "text",
            "structured_data": {},
            "confidence": 0.5,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert result["raw_fields"] == []
        assert result.get("status") != "error"

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_uses_summarize_prompt_when_no_template(self, mock_get_provider):
        """In no-template mode, the prompt should be the SUMMARIZE_PROMPT."""
        from docmind.library.pipeline.extraction.extract import extract_node, SUMMARIZE_PROMPT

        # Return a summarize-style response
        response = {
            "content": "text",
            "structured_data": {
                "document_type": "cv",
                "summary": "A CV.",
                "language": "English",
                "sections": [],
                "entities": [],
            },
            "confidence": 0.9,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state(template_type=None)
        extract_node(state)

        call_args = provider.extract.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[1].get("prompt", "")
        assert prompt == SUMMARIZE_PROMPT


class TestSummarizeMode:
    """Tests for unstructured document summarization."""

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_summarize_produces_summary_fields(self, mock_get_provider):
        """Summarization should produce summary, document_type, and language fields."""
        from docmind.library.pipeline.extraction.extract import extract_node

        response = {
            "content": "text",
            "structured_data": {
                "document_type": "cv",
                "summary": "Muhammad Ziad Alfian is a Mobile App Developer.",
                "language": "English",
                "sections": [
                    {"name": "Education", "content_preview": "Computer Science", "page_number": 1},
                ],
                "entities": [
                    {"type": "person", "value": "Muhammad Ziad Alfian", "page_number": 1},
                ],
            },
            "confidence": 0.9,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state(template_type=None)
        result = extract_node(state)

        fields = result["raw_fields"]
        assert len(fields) > 0

        field_keys = [f["field_key"] for f in fields]
        assert "summary" in field_keys
        assert "document_type" in field_keys
        assert "language" in field_keys
        assert result["document_type"] == "cv"

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_summarize_creates_section_fields(self, mock_get_provider):
        """Sections should become field_type='section' fields."""
        from docmind.library.pipeline.extraction.extract import extract_node

        response = {
            "content": "text",
            "structured_data": {
                "document_type": "report",
                "summary": "A report.",
                "language": "English",
                "sections": [
                    {"name": "Introduction", "content_preview": "This report covers...", "page_number": 1},
                    {"name": "Financials", "content_preview": "Revenue grew 15%", "page_number": 2},
                ],
                "entities": [],
            },
            "confidence": 0.9,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state(template_type=None)
        result = extract_node(state)

        section_fields = [f for f in result["raw_fields"] if f["field_type"] == "section"]
        assert len(section_fields) == 2
        assert section_fields[0]["field_key"] == "Introduction"

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_summarize_creates_entity_fields(self, mock_get_provider):
        """Entities should become field_type='entity' fields."""
        from docmind.library.pipeline.extraction.extract import extract_node

        response = {
            "content": "text",
            "structured_data": {
                "document_type": "letter",
                "summary": "A letter.",
                "language": "English",
                "sections": [],
                "entities": [
                    {"type": "person", "value": "John Doe", "page_number": 1},
                    {"type": "org", "value": "Acme Corp", "page_number": 1},
                ],
            },
            "confidence": 0.9,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state(template_type=None)
        result = extract_node(state)

        entity_fields = [f for f in result["raw_fields"] if f["field_type"] == "entity"]
        assert len(entity_fields) == 2
        assert entity_fields[0]["field_key"] == "person"
        assert entity_fields[0]["field_value"] == "John Doe"

    @patch("docmind.library.pipeline.extraction.extract.get_vlm_provider")
    def test_summarize_audit_mode(self, mock_get_provider):
        """Audit entry should record mode as 'summarize'."""
        from docmind.library.pipeline.extraction.extract import extract_node

        response = {
            "content": "text",
            "structured_data": {
                "document_type": "cv",
                "summary": "A CV.",
                "language": "English",
                "sections": [],
                "entities": [],
            },
            "confidence": 0.9,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state(template_type=None)
        result = extract_node(state)

        audit = result["audit_entries"][-1]
        assert audit["input_summary"]["mode"] == "summarize"
