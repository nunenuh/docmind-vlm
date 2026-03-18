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
        extract_response = {
            "content": "Extracted content",
            "structured_data": {
                "fields": [
                    {
                        "field_type": "key_value",
                        "field_key": "invoice_number",
                        "field_value": "INV-001",
                        "page_number": 1,
                        "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.05},
                        "confidence": 0.95,
                    },
                    {
                        "field_type": "key_value",
                        "field_key": "total",
                        "field_value": "$500.00",
                        "page_number": 1,
                        "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05},
                        "confidence": 0.88,
                    },
                ],
                "document_type": "invoice",
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

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_extracts_fields_from_vlm_response(self, mock_get_provider):
        """extract_node returns raw_fields parsed from VLM response."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert len(result["raw_fields"]) == 2
        assert result["raw_fields"][0]["field_key"] == "invoice_number"
        assert result["raw_fields"][0]["field_value"] == "INV-001"
        assert result["raw_fields"][1]["field_key"] == "total"

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_attaches_vlm_confidence_to_fields(self, mock_get_provider):
        """Each field gets vlm_confidence from its own confidence or VLM response fallback."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert result["raw_fields"][0]["vlm_confidence"] == 0.95
        assert result["raw_fields"][1]["vlm_confidence"] == 0.88

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_does_not_mutate_original_vlm_fields(self, mock_get_provider):
        """Original field dicts from VLM response must not be mutated."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider
        original_fields = provider.extract.return_value["structured_data"]["fields"]

        state = _make_state()
        extract_node(state)

        assert "vlm_confidence" not in original_fields[0]
        assert "vlm_confidence" not in original_fields[1]

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_vlm_confidence_falls_back_to_response_level(self, mock_get_provider):
        """If field has no confidence, use VLM response-level confidence."""
        from docmind.library.pipeline.processing import extract_node

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

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_returns_document_type_from_vlm(self, mock_get_provider):
        """document_type is extracted from VLM response structured_data."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert result["document_type"] == "invoice"

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_classifies_when_no_document_type_detected(self, mock_get_provider):
        """If general mode and no document_type in response, calls classify()."""
        from docmind.library.pipeline.processing import extract_node

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

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_skips_classify_when_document_type_present(self, mock_get_provider):
        """If document_type is already in response, don't call classify()."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        extract_node(state)

        provider.classify.assert_not_called()

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_serializes_vlm_response(self, mock_get_provider):
        """vlm_response in result contains content, confidence, model, usage."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        vlm = result["vlm_response"]
        assert "content" in vlm
        assert "confidence" in vlm
        assert "model" in vlm
        assert "usage" in vlm

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_creates_audit_entry(self, mock_get_provider):
        """extract_node appends audit entry with step_name='extract'."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert len(result["audit_entries"]) == 1
        entry = result["audit_entries"][0]
        assert entry["step_name"] == "extract"
        assert entry["step_order"] == 2
        assert entry["input_summary"]["mode"] == "general"
        assert entry["output_summary"]["field_count"] == 2
        assert entry["output_summary"]["vlm_model"] == "test-model"
        assert entry["parameters"]["provider"] == "test-provider"
        assert entry["parameters"]["model"] == "test-model"
        assert isinstance(entry["duration_ms"], int)


class TestExtractNodeCallbackAndErrors:
    """Tests for callback invocation and error handling."""

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_callback_invoked_at_substeps(self, mock_get_provider):
        """progress_callback is called multiple times during extraction."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider
        callback = MagicMock()

        state = _make_state(callback=callback)
        extract_node(state)

        assert callback.call_count >= 3

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_works_without_callback(self, mock_get_provider):
        """extract_node works when callback is None."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(callback=None)
        result = extract_node(state)

        assert len(result["raw_fields"]) == 2

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_returns_error_on_provider_failure(self, mock_get_provider):
        """If VLM provider raises, returns status='error'."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        provider.extract = AsyncMock(side_effect=RuntimeError("VLM API timeout"))
        mock_get_provider.return_value = provider

        state = _make_state()
        result = extract_node(state)

        assert result["status"] == "error"
        assert result["error_message"] == "Extraction failed. See server logs for details."

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_handles_malformed_vlm_response_missing_fields(self, mock_get_provider):
        """If VLM response has no 'fields' key, treats as empty list."""
        from docmind.library.pipeline.processing import extract_node

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

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_uses_general_prompt_when_no_template(self, mock_get_provider):
        """In general mode, the prompt passed to provider.extract is the general prompt."""
        from docmind.library.pipeline.processing import extract_node, GENERAL_EXTRACTION_PROMPT

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(template_type=None)
        extract_node(state)

        call_args = provider.extract.call_args
        assert call_args.kwargs.get("prompt") == GENERAL_EXTRACTION_PROMPT or call_args[1].get("prompt") == GENERAL_EXTRACTION_PROMPT
