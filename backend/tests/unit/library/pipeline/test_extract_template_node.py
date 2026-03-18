"""
Unit tests for extract_node pipeline function — template mode.

VLM provider is fully mocked. Tests verify template prompt construction,
required field validation, unknown template handling, and audit entries.
"""
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import numpy as np
import pytest


def _make_fake_provider(
    extract_response: dict | None = None,
    provider_name: str = "test-provider",
    model_name: str = "test-model",
):
    """Create a mock VLM provider."""
    provider = MagicMock()
    type(provider).provider_name = PropertyMock(return_value=provider_name)
    type(provider).model_name = PropertyMock(return_value=model_name)

    if extract_response is None:
        extract_response = {
            "content": "Extracted invoice fields",
            "structured_data": {
                "fields": [
                    {
                        "field_type": "key_value",
                        "field_key": "invoice_number",
                        "field_value": "INV-2024-001",
                        "page_number": 1,
                        "bounding_box": {"x": 0.6, "y": 0.05, "width": 0.3, "height": 0.04},
                        "confidence": 0.95,
                        "is_required": True,
                        "is_missing": False,
                    },
                    {
                        "field_type": "key_value",
                        "field_key": "date",
                        "field_value": "2024-01-15",
                        "page_number": 1,
                        "bounding_box": {"x": 0.6, "y": 0.1, "width": 0.2, "height": 0.04},
                        "confidence": 0.92,
                        "is_required": True,
                        "is_missing": False,
                    },
                    {
                        "field_type": "key_value",
                        "field_key": "total_amount",
                        "field_value": "$1,250.00",
                        "page_number": 1,
                        "bounding_box": {"x": 0.7, "y": 0.85, "width": 0.2, "height": 0.04},
                        "confidence": 0.88,
                        "is_required": True,
                        "is_missing": False,
                    },
                    {
                        "field_type": "key_value",
                        "field_key": "vendor_name",
                        "field_value": "Acme Corp",
                        "page_number": 1,
                        "bounding_box": {"x": 0.1, "y": 0.05, "width": 0.3, "height": 0.04},
                        "confidence": 0.90,
                        "is_required": True,
                        "is_missing": False,
                    },
                ],
                "document_type": "invoice",
            },
            "confidence": 0.91,
            "model": "test-model",
            "usage": {"prompt_tokens": 200, "completion_tokens": 100},
            "raw_response": {},
        }

    provider.extract = AsyncMock(return_value=extract_response)
    provider.classify = AsyncMock()
    return provider


def _make_state(
    template_type: str | None = "invoice",
    page_images: list | None = None,
    callback: object | None = None,
) -> dict:
    """Build a ProcessingState for template extraction."""
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


class TestGetTemplateConfig:
    """Tests for the _get_template_config helper."""

    def test_returns_config_for_invoice(self):
        from docmind.library.pipeline.processing import _get_template_config

        config = _get_template_config("invoice")
        assert config is not None
        assert "invoice_number" in config["required_fields"]
        assert "date" in config["required_fields"]
        assert "total_amount" in config["required_fields"]
        assert "vendor_name" in config["required_fields"]
        assert "due_date" in config["optional_fields"]

    def test_returns_config_for_receipt(self):
        from docmind.library.pipeline.processing import _get_template_config

        config = _get_template_config("receipt")
        assert config is not None
        assert "date" in config["required_fields"]
        assert "total_amount" in config["required_fields"]
        assert "merchant_name" in config["required_fields"]

    def test_returns_config_for_medical_report(self):
        from docmind.library.pipeline.processing import _get_template_config

        config = _get_template_config("medical_report")
        assert config is not None
        assert "patient_name" in config["required_fields"]

    def test_returns_config_for_contract(self):
        from docmind.library.pipeline.processing import _get_template_config

        config = _get_template_config("contract")
        assert config is not None
        assert "parties" in config["required_fields"]

    def test_returns_config_for_id_document(self):
        from docmind.library.pipeline.processing import _get_template_config

        config = _get_template_config("id_document")
        assert config is not None
        assert "full_name" in config["required_fields"]

    def test_returns_none_for_unknown_type(self):
        from docmind.library.pipeline.processing import _get_template_config

        config = _get_template_config("unknown_type")
        assert config is None


class TestExtractNodeTemplateMode:
    """Tests for template-based extraction."""

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_uses_template_prompt_with_required_fields(self, mock_get_provider):
        """In template mode, prompt includes required and optional fields."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(template_type="invoice")
        extract_node(state)

        call_args = provider.extract.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[1].get("prompt", "")
        assert "invoice_number" in prompt
        assert "total_amount" in prompt
        assert "vendor_name" in prompt

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_returns_error_for_unknown_template(self, mock_get_provider):
        """Unknown template_type returns status='error' without calling VLM."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(template_type="nonexistent_type")
        result = extract_node(state)

        assert result["status"] == "error"
        assert "Unknown template type" in result["error_message"]
        assert "nonexistent_type" not in result["error_message"]
        provider.extract.assert_not_called()

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_extracts_fields_in_template_mode(self, mock_get_provider):
        """Template mode returns raw_fields from VLM response."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(template_type="invoice")
        result = extract_node(state)

        assert len(result["raw_fields"]) == 4
        field_keys = [f["field_key"] for f in result["raw_fields"]]
        assert "invoice_number" in field_keys
        assert "total_amount" in field_keys

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_sets_document_type_to_template_type(self, mock_get_provider):
        """In template mode, document_type defaults to template_type."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(template_type="invoice")
        result = extract_node(state)

        assert result["document_type"] == "invoice"

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_does_not_call_classify_in_template_mode(self, mock_get_provider):
        """Template mode skips classify() since type is known."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(template_type="invoice")
        extract_node(state)

        provider.classify.assert_not_called()

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_audit_entry_shows_template_mode(self, mock_get_provider):
        """Audit entry input_summary includes mode='template' and template_type."""
        from docmind.library.pipeline.processing import extract_node

        provider = _make_fake_provider()
        mock_get_provider.return_value = provider

        state = _make_state(template_type="invoice")
        result = extract_node(state)

        entry = result["audit_entries"][-1]
        assert entry["input_summary"]["mode"] == "template"
        assert entry["input_summary"]["template_type"] == "invoice"

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_handles_missing_fields_in_vlm_response(self, mock_get_provider):
        """If VLM returns fields with is_missing=True, they pass through."""
        from docmind.library.pipeline.processing import extract_node

        response = {
            "content": "partial extraction",
            "structured_data": {
                "fields": [
                    {
                        "field_type": "key_value",
                        "field_key": "invoice_number",
                        "field_value": None,
                        "page_number": 1,
                        "bounding_box": {},
                        "confidence": 0.0,
                        "is_required": True,
                        "is_missing": True,
                    },
                ],
                "document_type": "invoice",
            },
            "confidence": 0.3,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state(template_type="invoice")
        result = extract_node(state)

        assert len(result["raw_fields"]) == 1
        assert result["raw_fields"][0]["is_missing"] is True

    @patch("docmind.library.pipeline.processing.get_vlm_provider")
    def test_receipt_template_uses_correct_fields(self, mock_get_provider):
        """Receipt template prompt includes merchant_name, not vendor_name."""
        from docmind.library.pipeline.processing import extract_node

        response = {
            "content": "receipt",
            "structured_data": {"fields": [], "document_type": "receipt"},
            "confidence": 0.5,
            "model": "test",
            "usage": {},
            "raw_response": {},
        }
        provider = _make_fake_provider(extract_response=response)
        mock_get_provider.return_value = provider

        state = _make_state(template_type="receipt")
        extract_node(state)

        call_args = provider.extract.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[1].get("prompt", "")
        assert "merchant_name" in prompt
        assert "total_amount" in prompt
