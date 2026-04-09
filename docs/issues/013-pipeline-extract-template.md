# Issue #13: Pipeline Extract Node — Template (Schema-Aware) Mode

## Summary

Extend the `extract_node` to support template-based (schema-aware) extraction. When `template_type` is set in the processing state, the node auto-detects document type via VLM `classify()` (if not already specified), loads the template schema from `data/templates/`, constructs a schema-aware extraction prompt with required/optional fields, runs VLM extraction, validates that all required fields are present, and flags missing required fields. This builds on the general extraction from issue #12.

## Context
- **Phase**: 3 — Processing Pipeline
- **Priority**: P0
- **Labels**: `phase-3-pipeline`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: #12 (extract_node general mode must exist first)
- **Branch**: `feat/13-pipeline-extract-template`
- **Estimated scope**: M

## Specs to Read
- `specs/backend/pipeline-processing.md` — Template extraction prompt, `_get_template_config()`, extract node flow
- `specs/backend/api.md` — Templates endpoint, `TemplateResponse` schema
- `specs/backend/services.md` — Template configuration mapping

## Current State (Scaffold)

After issue #12, `extract_node` handles general mode. Template mode logic is not yet implemented.

**Template JSON files exist but are empty** (`data/templates/*.json`):
```json
{}
```

**Template types defined in spec** (hardcoded in `_get_template_config()`):
- `invoice`: required `[invoice_number, date, total_amount, vendor_name]`
- `receipt`: required `[date, total_amount, merchant_name]`
- `medical_report`: required `[patient_name, report_date, report_type]`
- `contract`: required `[parties, effective_date, contract_type]`
- `id_document`: required `[full_name, document_number, date_of_birth]`

**`TEMPLATE_EXTRACTION_PROMPT`** from spec:
```
Analyze this document as a {template_type}.

Extract the following required fields: {required_fields}
Also extract if present: {optional_fields}

For each field, return a JSON object with:
- "field_type": one of "key_value", "table_cell", "entity", "text_block"
- "field_key": the field name from the template
- "field_value": the extracted text value (null if not found)
- "page_number": which page (1-indexed)
- "bounding_box": {{"x": float, "y": float, "width": float, "height": float}}
- "confidence": your confidence (0.0-1.0)
- "is_required": true if required
- "is_missing": true if not found

Return a JSON object: {{"fields": [...], "document_type": "{template_type}"}}
```

## Requirements

### Functional

1. Add `TEMPLATE_EXTRACTION_PROMPT` constant to `processing.py`.
2. Add `_get_template_config(template_type: str) -> dict | None` function that returns `{"required_fields": [...], "optional_fields": [...]}` for known template types, or `None` for unknown types.
3. When `template_type` is set in state:
   a. Look up template config via `_get_template_config(template_type)`.
   b. If config is `None`, return `{"status": "error", "error_message": "Unknown template type: {template_type}"}`.
   c. Format `TEMPLATE_EXTRACTION_PROMPT` with `template_type`, `required_fields`, `optional_fields`.
   d. Call VLM `extract()` with the template prompt.
4. VLM response fields should include `is_required` and `is_missing` markers from the VLM.
5. Audit entry `input_summary` should include `mode="template"` and `template_type`.
6. The `extract_node` must handle both general and template mode via a conditional branch (already partially specified in #12).

### Non-Functional

- Unknown template types must fail fast with a clear error message.
- Template config is hardcoded (matching the spec), not loaded from JSON files yet.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/pipeline/test_extract_template_node.py`

```python
"""
Unit tests for extract_node pipeline function — template mode.

VLM provider is fully mocked. Tests verify template prompt construction,
required field validation, unknown template handling, and audit entries.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
import numpy as np


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

        call_kwargs = provider.extract.call_args.kwargs if provider.extract.call_args.kwargs else {}
        call_args = provider.extract.call_args
        # The prompt should contain required field names
        prompt = call_kwargs.get("prompt") or call_args[1].get("prompt", "")
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
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/pipeline/processing.py`

**Implementation guidance**:

1. Add the `TEMPLATE_EXTRACTION_PROMPT` constant.
2. Add `_get_template_config(template_type: str) -> dict | None` with the hardcoded template definitions from the spec.
3. Extend `extract_node` to handle the template branch:
   - Check `template_type` in state
   - If set: look up config, return error if `None`, format template prompt
   - If not set: use general prompt (already from #12)
   - Call VLM extract with the appropriate prompt
   - In template mode, skip classify since type is known

### Step 3: Refactor (IMPROVE)
- Consider extracting prompt building into `_build_extraction_prompt(template_type, config)` helper
- Ensure template config is easy to extend (consider loading from JSON files in future)

## Acceptance Criteria
- [ ] `TEMPLATE_EXTRACTION_PROMPT` constant is defined
- [ ] `_get_template_config()` returns correct configs for all 5 template types and `None` for unknowns
- [ ] Template mode uses `TEMPLATE_EXTRACTION_PROMPT` formatted with required/optional fields
- [ ] Unknown template type returns `status="error"` without calling VLM
- [ ] Template mode skips `classify()` call
- [ ] Audit entry shows `mode="template"` and `template_type`
- [ ] Fields with `is_missing=True` from VLM pass through correctly
- [ ] Both general (#12) and template tests pass
- [ ] All unit tests pass

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/library/pipeline/processing.py` | Modify | Add `TEMPLATE_EXTRACTION_PROMPT`, `_get_template_config()`, extend `extract_node` |
| `backend/tests/unit/library/pipeline/test_extract_template_node.py` | Create | Unit tests for template mode extraction |

## Verification

```bash
# Run template extraction tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/pipeline/test_extract_template_node.py -v

# Run all extract tests (general + template)
python -m pytest backend/tests/unit/library/pipeline/test_extract_node.py backend/tests/unit/library/pipeline/test_extract_template_node.py -v

# Run with coverage
python -m pytest backend/tests/unit/library/pipeline/ -v --cov=docmind.library.pipeline.processing --cov-report=term-missing

# Verify imports
python -c "from docmind.library.pipeline.processing import _get_template_config, TEMPLATE_EXTRACTION_PROMPT; print('OK')"
```
