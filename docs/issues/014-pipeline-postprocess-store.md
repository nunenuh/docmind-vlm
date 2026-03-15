# Issue #14: Pipeline Postprocess + Store Nodes

## Summary

Implement the `postprocess_node` and `store_node` LangGraph node functions. The postprocess node merges VLM confidence scores with CV region quality scores using a weighted formula (`final = vlm * 0.7 + cv * 0.3`), validates extracted fields against template requirements (adding placeholders for missing required fields), and generates human-readable explanations for low-confidence fields. The store node persists the `Extraction`, `ExtractedField`, and `AuditEntry` records to the database via SQLAlchemy async sessions, and updates the document status to "ready".

## Context
- **Phase**: 3 — Processing Pipeline
- **Priority**: P0
- **Labels**: `phase-3-pipeline`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: #12, #13 (extract_node produces `raw_fields`, `quality_map`)
- **Branch**: `feat/14-pipeline-postprocess-store`
- **Estimated scope**: L

## Specs to Read
- `specs/backend/pipeline-processing.md` — Postprocess node (confidence merging, validation, explanations) and store node (DB persistence)
- `specs/backend/services.md` — ExtractionRepository for field persistence
- `specs/backend/api.md` — ORM models (`Extraction`, `ExtractedField`, `AuditEntry`, `Document`)

## Current State (Scaffold)

**`backend/src/docmind/library/pipeline/processing.py`** — After issues #11-#13, contains `preprocess_node` and `extract_node`. No `postprocess_node` or `store_node` exists.

**ORM Models** (`backend/src/docmind/dbase/sqlalchemy/models.py`) — Fully defined:
```python
class Extraction(Base):
    __tablename__ = "extractions"
    id, document_id, mode, template_type, processing_time_ms, created_at
    fields: list["ExtractedField"]
    audit_entries: list["AuditEntry"]

class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id, extraction_id, field_type, field_key, field_value, page_number,
    bounding_box, confidence, vlm_confidence, cv_quality_score,
    is_required, is_missing

class AuditEntry(Base):
    __tablename__ = "audit_entries"
    id, extraction_id, step_name, step_order, input_summary,
    output_summary, parameters, duration_ms
```

**Extraction Repository** (`backend/src/docmind/modules/extractions/repositories.py`) — Stub:
```python
class ExtractionRepository:
    async def get_latest_extraction(self, document_id: str):
        raise NotImplementedError
    async def get_fields(self, extraction_id: str):
        raise NotImplementedError
    async def get_audit_trail(self, extraction_id: str):
        raise NotImplementedError
```

## Requirements

### Functional — Postprocess Node

1. `postprocess_node(state: dict) -> dict` reads `raw_fields`, `quality_map`, `template_type` from state.
2. **Confidence merging formula**: `final_confidence = vlm_confidence * 0.7 + cv_quality_score * 0.3`
   - Constants: `CONFIDENCE_VLM_WEIGHT = 0.7`, `CONFIDENCE_CV_WEIGHT = 0.3`
   - Result clamped to `[0.0, 1.0]`, rounded to 4 decimal places.
3. **CV quality lookup**: `_lookup_cv_quality(bounding_box, quality_map)` maps the field's bounding box center to the nearest quality grid cell. Returns `0.5` as fallback.
4. **Template validation**: `_validate_template_fields(fields, template_type)` adds missing required fields as placeholder entries with `confidence=0.0`, `is_missing=True`, `is_required=True`.
5. **Low-confidence explanations**: `_generate_low_confidence_explanation(field, cv_quality)` returns a human-readable string for fields with `confidence < 0.5`. Returns `None` for fields above threshold.
6. Each enhanced field gets: `confidence` (merged), `vlm_confidence`, `cv_quality_score`, `is_required`, `is_missing`, optional `low_confidence_reason`.
7. Build `comparison_data` with `corrected` (field IDs where confidence changed by >0.05) and `added` (field IDs added by template validation).
8. Audit entry with `step_name="postprocess"`, `step_order=3`.
9. Return `enhanced_fields`, `comparison_data`, `audit_entries`.

### Functional — Store Node

10. `store_node(state: dict) -> dict` reads `document_id`, `enhanced_fields`, `audit_entries`, `document_type`, `page_count`, `template_type` from state.
11. Generate a new `extraction_id` (UUID4).
12. In a single DB transaction via `async_session()`:
    a. Insert `Extraction` record.
    b. Insert all `ExtractedField` records.
    c. Insert all `AuditEntry` records (from accumulated `audit_entries`).
    d. Update `Document` status to `"ready"`, set `document_type` and `page_count`.
13. Uses `asyncio.run()` to execute async DB operations from sync context.
14. Audit entry with `step_name="store"`, `step_order=4`.
15. Return `extraction_id`, `status="ready"`, `audit_entries`.

### Non-Functional

- Postprocess helpers are pure functions (testable without DB).
- Store node uses SQLAlchemy async sessions; tests mock `async_session`.
- Both nodes must not import from `docmind.modules.*`.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/pipeline/test_postprocess_node.py`

```python
"""
Unit tests for postprocess_node and its helper functions.

Tests verify confidence merging formula, CV quality lookup,
template validation, low-confidence explanations, and audit entries.
No database interaction — all pure functions.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch
import numpy as np


def _make_raw_field(
    field_key: str = "amount",
    confidence: float = 0.9,
    vlm_confidence: float | None = None,
    bounding_box: dict | None = None,
    is_required: bool = False,
    is_missing: bool = False,
    field_id: str | None = None,
) -> dict:
    """Create a raw extracted field dict."""
    return {
        "id": field_id or str(uuid.uuid4()),
        "field_type": "key_value",
        "field_key": field_key,
        "field_value": "100.00",
        "page_number": 1,
        "bounding_box": bounding_box or {"x": 0.5, "y": 0.5, "width": 0.2, "height": 0.05},
        "confidence": confidence,
        "vlm_confidence": vlm_confidence if vlm_confidence is not None else confidence,
        "is_required": is_required,
        "is_missing": is_missing,
    }


def _make_state(
    raw_fields: list[dict] | None = None,
    quality_map: dict | None = None,
    template_type: str | None = None,
    callback: object | None = None,
) -> dict:
    """Build a ProcessingState for postprocess_node."""
    return {
        "document_id": "doc-123",
        "user_id": "user-456",
        "file_bytes": b"",
        "file_type": "pdf",
        "template_type": template_type,
        "page_images": [],
        "page_count": 1,
        "quality_map": quality_map or {},
        "skew_angles": [],
        "raw_fields": raw_fields or [_make_raw_field()],
        "vlm_response": {},
        "document_type": "invoice",
        "enhanced_fields": [],
        "comparison_data": {},
        "extraction_id": "",
        "status": "processing",
        "error_message": None,
        "audit_entries": [],
        "progress_callback": callback,
    }


class TestMergeConfidence:
    """Tests for _merge_confidence helper."""

    def test_standard_merge(self):
        from docmind.library.pipeline.processing import _merge_confidence

        result = _merge_confidence(vlm_confidence=0.9, cv_quality=0.8)
        expected = 0.9 * 0.7 + 0.8 * 0.3  # 0.63 + 0.24 = 0.87
        assert abs(result - expected) < 0.001

    def test_clamped_to_max_1(self):
        from docmind.library.pipeline.processing import _merge_confidence

        result = _merge_confidence(vlm_confidence=1.0, cv_quality=1.0)
        assert result <= 1.0

    def test_clamped_to_min_0(self):
        from docmind.library.pipeline.processing import _merge_confidence

        result = _merge_confidence(vlm_confidence=0.0, cv_quality=0.0)
        assert result >= 0.0

    def test_rounded_to_4_decimals(self):
        from docmind.library.pipeline.processing import _merge_confidence

        result = _merge_confidence(vlm_confidence=0.333, cv_quality=0.777)
        assert len(str(result).split(".")[-1]) <= 4

    def test_vlm_weighted_more_than_cv(self):
        """VLM confidence has 70% weight vs CV 30%."""
        from docmind.library.pipeline.processing import _merge_confidence

        high_vlm = _merge_confidence(vlm_confidence=1.0, cv_quality=0.0)
        high_cv = _merge_confidence(vlm_confidence=0.0, cv_quality=1.0)
        assert high_vlm > high_cv


class TestLookupCvQuality:
    """Tests for _lookup_cv_quality helper."""

    def test_maps_bbox_center_to_grid_cell(self):
        from docmind.library.pipeline.processing import _lookup_cv_quality

        quality_map = {"1,2": {"overall_score": 0.85}}
        bbox = {"x": 0.5, "y": 0.3, "width": 0.1, "height": 0.1}
        # center_x = 0.55, center_y = 0.35
        # grid_col = int(0.55 * 4) = 2, grid_row = int(0.35 * 4) = 1
        result = _lookup_cv_quality(bbox, quality_map)
        assert result == 0.85

    def test_returns_fallback_when_no_quality_map(self):
        from docmind.library.pipeline.processing import _lookup_cv_quality

        result = _lookup_cv_quality({"x": 0.5, "y": 0.5}, {})
        assert result == 0.5

    def test_returns_fallback_when_no_bbox(self):
        from docmind.library.pipeline.processing import _lookup_cv_quality

        result = _lookup_cv_quality({}, {"0,0": {"overall_score": 0.9}})
        assert result == 0.5

    def test_returns_fallback_when_cell_not_found(self):
        from docmind.library.pipeline.processing import _lookup_cv_quality

        quality_map = {"0,0": {"overall_score": 0.9}}
        bbox = {"x": 0.9, "y": 0.9, "width": 0.05, "height": 0.05}
        result = _lookup_cv_quality(bbox, quality_map)
        # Cell (3,3) not in map -> fallback
        assert result == 0.5


class TestGenerateLowConfidenceExplanation:
    """Tests for _generate_low_confidence_explanation."""

    def test_returns_none_for_high_confidence(self):
        from docmind.library.pipeline.processing import _generate_low_confidence_explanation

        field = {"confidence": 0.8, "vlm_confidence": 0.8}
        result = _generate_low_confidence_explanation(field, cv_quality=0.9)
        assert result is None

    def test_returns_explanation_for_low_vlm_confidence(self):
        from docmind.library.pipeline.processing import _generate_low_confidence_explanation

        field = {"confidence": 0.3, "vlm_confidence": 0.3}
        result = _generate_low_confidence_explanation(field, cv_quality=0.8)
        assert result is not None
        assert "VLM" in result

    def test_returns_explanation_for_poor_image_quality(self):
        from docmind.library.pipeline.processing import _generate_low_confidence_explanation

        field = {"confidence": 0.4, "vlm_confidence": 0.6}
        result = _generate_low_confidence_explanation(field, cv_quality=0.2)
        assert result is not None
        assert "quality" in result.lower() or "blur" in result.lower() or "noise" in result.lower()

    def test_returns_explanation_for_missing_field(self):
        from docmind.library.pipeline.processing import _generate_low_confidence_explanation

        field = {"confidence": 0.0, "vlm_confidence": 0.0, "is_missing": True}
        result = _generate_low_confidence_explanation(field, cv_quality=0.5)
        assert result is not None
        assert "not found" in result or "missing" in result

    def test_returns_generic_explanation_when_no_specific_reason(self):
        from docmind.library.pipeline.processing import _generate_low_confidence_explanation

        field = {"confidence": 0.4, "vlm_confidence": 0.6}
        result = _generate_low_confidence_explanation(field, cv_quality=0.8)
        assert result is not None
        assert "threshold" in result or "below" in result


class TestValidateTemplateFields:
    """Tests for _validate_template_fields."""

    def test_adds_missing_required_fields_as_placeholders(self):
        from docmind.library.pipeline.processing import _validate_template_fields

        fields = [_make_raw_field(field_key="invoice_number")]
        result = _validate_template_fields(fields, "invoice")

        keys = [f["field_key"] for f in result]
        # invoice requires: invoice_number, date, total_amount, vendor_name
        assert "date" in keys
        assert "total_amount" in keys
        assert "vendor_name" in keys

    def test_placeholder_fields_have_correct_markers(self):
        from docmind.library.pipeline.processing import _validate_template_fields

        fields = []  # no fields extracted
        result = _validate_template_fields(fields, "invoice")

        for field in result:
            assert field["is_required"] is True
            assert field["is_missing"] is True
            assert field["confidence"] == 0.0
            assert field["field_value"] == ""

    def test_marks_existing_required_fields(self):
        from docmind.library.pipeline.processing import _validate_template_fields

        fields = [_make_raw_field(field_key="invoice_number", confidence=0.9)]
        result = _validate_template_fields(fields, "invoice")

        inv_field = next(f for f in result if f["field_key"] == "invoice_number")
        assert inv_field["is_required"] is True
        assert inv_field.get("is_missing", False) is False

    def test_returns_fields_unchanged_when_no_template(self):
        from docmind.library.pipeline.processing import _validate_template_fields

        fields = [_make_raw_field(field_key="random_field")]
        result = _validate_template_fields(fields, None)

        assert len(result) == 1
        assert result[0]["field_key"] == "random_field"

    def test_does_not_duplicate_existing_required_fields(self):
        from docmind.library.pipeline.processing import _validate_template_fields

        fields = [
            _make_raw_field(field_key="invoice_number"),
            _make_raw_field(field_key="date"),
            _make_raw_field(field_key="total_amount"),
            _make_raw_field(field_key="vendor_name"),
        ]
        result = _validate_template_fields(fields, "invoice")

        keys = [f["field_key"] for f in result]
        assert keys.count("invoice_number") == 1
        assert keys.count("date") == 1


class TestPostprocessNode:
    """Integration tests for postprocess_node."""

    def test_merges_confidence_on_all_fields(self):
        from docmind.library.pipeline.processing import postprocess_node

        quality_map = {"2,2": {"overall_score": 0.8}}
        fields = [_make_raw_field(vlm_confidence=0.9, bounding_box={"x": 0.5, "y": 0.5, "width": 0.1, "height": 0.1})]
        state = _make_state(raw_fields=fields, quality_map=quality_map)
        result = postprocess_node(state)

        enhanced = result["enhanced_fields"]
        assert len(enhanced) == 1
        # Verify merged confidence is different from original
        assert "confidence" in enhanced[0]
        assert "vlm_confidence" in enhanced[0]
        assert "cv_quality_score" in enhanced[0]

    def test_creates_comparison_data(self):
        from docmind.library.pipeline.processing import postprocess_node

        state = _make_state()
        result = postprocess_node(state)

        assert "comparison_data" in result
        assert "corrected" in result["comparison_data"]
        assert "added" in result["comparison_data"]

    def test_creates_audit_entry(self):
        from docmind.library.pipeline.processing import postprocess_node

        state = _make_state()
        result = postprocess_node(state)

        assert len(result["audit_entries"]) >= 1
        entry = result["audit_entries"][-1]
        assert entry["step_name"] == "postprocess"
        assert entry["step_order"] == 3

    def test_returns_error_on_exception(self):
        from docmind.library.pipeline.processing import postprocess_node

        # Force an error by providing bad data
        state = _make_state()
        state["raw_fields"] = "not-a-list"  # type: ignore
        result = postprocess_node(state)

        assert result["status"] == "error"
        assert "Postprocessing failed" in result["error_message"]

    def test_callback_invoked(self):
        from docmind.library.pipeline.processing import postprocess_node

        callback = MagicMock()
        state = _make_state(callback=callback)
        postprocess_node(state)

        assert callback.call_count >= 2
```

**Test file**: `backend/tests/unit/library/pipeline/test_store_node.py`

```python
"""
Unit tests for store_node pipeline function.

Database operations are mocked. Tests verify that store_node
creates the correct ORM objects, calls commit, updates document
status, and handles errors properly.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone


def _make_state(
    enhanced_fields: list[dict] | None = None,
    audit_entries: list[dict] | None = None,
    callback: object | None = None,
) -> dict:
    """Build a ProcessingState for store_node."""
    if enhanced_fields is None:
        enhanced_fields = [
            {
                "id": str(uuid.uuid4()),
                "field_type": "key_value",
                "field_key": "total",
                "field_value": "$500",
                "page_number": 1,
                "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05},
                "confidence": 0.85,
                "vlm_confidence": 0.9,
                "cv_quality_score": 0.7,
                "is_required": False,
                "is_missing": False,
            },
        ]
    if audit_entries is None:
        audit_entries = [
            {
                "step_name": "preprocess",
                "step_order": 1,
                "input_summary": {},
                "output_summary": {},
                "parameters": {},
                "duration_ms": 100,
            },
        ]
    return {
        "document_id": "doc-123",
        "user_id": "user-456",
        "file_bytes": b"",
        "file_type": "pdf",
        "template_type": None,
        "page_images": [],
        "page_count": 2,
        "quality_map": {},
        "skew_angles": [],
        "raw_fields": [],
        "vlm_response": {},
        "document_type": "invoice",
        "enhanced_fields": enhanced_fields,
        "comparison_data": {"corrected": [], "added": []},
        "extraction_id": "",
        "status": "processing",
        "error_message": None,
        "audit_entries": audit_entries,
        "progress_callback": callback,
    }


class TestStoreNode:
    """Tests for store_node database persistence."""

    @patch("docmind.library.pipeline.processing._persist_results", new_callable=AsyncMock)
    def test_returns_extraction_id(self, mock_persist):
        """store_node generates and returns a UUID extraction_id."""
        from docmind.library.pipeline.processing import store_node

        state = _make_state()
        result = store_node(state)

        assert "extraction_id" in result
        # Verify it's a valid UUID string
        uuid.UUID(result["extraction_id"])

    @patch("docmind.library.pipeline.processing._persist_results", new_callable=AsyncMock)
    def test_sets_status_to_ready(self, mock_persist):
        """store_node sets status to 'ready' on success."""
        from docmind.library.pipeline.processing import store_node

        state = _make_state()
        result = store_node(state)

        assert result["status"] == "ready"

    @patch("docmind.library.pipeline.processing._persist_results", new_callable=AsyncMock)
    def test_calls_persist_with_state_and_extraction_id(self, mock_persist):
        """store_node calls _persist_results with the state and extraction_id."""
        from docmind.library.pipeline.processing import store_node

        state = _make_state()
        result = store_node(state)

        mock_persist.assert_called_once()
        call_args = mock_persist.call_args
        assert call_args[0][0] is state or call_args[1].get("state") is state
        assert isinstance(call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("extraction_id"), str)

    @patch("docmind.library.pipeline.processing._persist_results", new_callable=AsyncMock)
    def test_creates_store_audit_entry(self, mock_persist):
        """store_node appends its own audit entry with step_name='store'."""
        from docmind.library.pipeline.processing import store_node

        state = _make_state()
        result = store_node(state)

        store_entry = result["audit_entries"][-1]
        assert store_entry["step_name"] == "store"
        assert store_entry["step_order"] == 4
        assert "extraction_id" in store_entry["output_summary"]

    @patch("docmind.library.pipeline.processing._persist_results", new_callable=AsyncMock)
    def test_preserves_existing_audit_entries(self, mock_persist):
        """Existing audit entries are preserved and store entry appended."""
        from docmind.library.pipeline.processing import store_node

        existing = [{"step_name": "preprocess", "step_order": 1}]
        state = _make_state(audit_entries=existing)
        result = store_node(state)

        assert len(result["audit_entries"]) == 2
        assert result["audit_entries"][0]["step_name"] == "preprocess"
        assert result["audit_entries"][-1]["step_name"] == "store"

    @patch("docmind.library.pipeline.processing._persist_results", new_callable=AsyncMock)
    def test_returns_error_on_db_failure(self, mock_persist):
        """If _persist_results raises, returns status='error'."""
        from docmind.library.pipeline.processing import store_node

        mock_persist.side_effect = RuntimeError("Connection refused")

        state = _make_state()
        result = store_node(state)

        assert result["status"] == "error"
        assert "Storage failed" in result["error_message"]

    @patch("docmind.library.pipeline.processing._persist_results", new_callable=AsyncMock)
    def test_callback_invoked(self, mock_persist):
        """progress_callback is called during store."""
        from docmind.library.pipeline.processing import store_node

        callback = MagicMock()
        state = _make_state(callback=callback)
        store_node(state)

        assert callback.call_count >= 1
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/pipeline/processing.py`

**Implementation guidance**:

1. Add constants at module level:
   ```python
   CONFIDENCE_VLM_WEIGHT = 0.7
   CONFIDENCE_CV_WEIGHT = 0.3
   LOW_CONFIDENCE_THRESHOLD = 0.5
   ```

2. Implement helper functions:
   - `_lookup_cv_quality(bounding_box, quality_map, page_height=4, page_width=4) -> float`
   - `_merge_confidence(vlm_confidence, cv_quality) -> float`
   - `_generate_low_confidence_explanation(field, cv_quality) -> str | None`
   - `_validate_template_fields(fields, template_type) -> list[dict]`

3. Implement `postprocess_node(state: dict) -> dict`:
   - Iterate raw_fields, look up CV quality, merge confidence
   - Validate template fields if template_type is set
   - Generate explanations for low-confidence fields
   - Build comparison_data
   - Build audit entry
   - Return state updates

4. Implement `_persist_results(state, extraction_id)` as an async helper:
   - Insert Extraction, ExtractedField, AuditEntry records
   - Update Document status

5. Implement `store_node(state: dict) -> dict`:
   - Generate extraction_id
   - Call `asyncio.run(_persist_results(state, extraction_id))`
   - Build audit entry
   - Return state updates
   - Wrap in try/except

### Step 3: Refactor (IMPROVE)
- Extract template required fields map into a module-level constant (shared with `_get_template_config`)
- Ensure `_persist_results` uses a single transaction (all or nothing)
- Add logging at key points

## Acceptance Criteria
- [ ] `_merge_confidence` implements `vlm * 0.7 + cv * 0.3`, clamped `[0, 1]`, rounded to 4 decimals
- [ ] `_lookup_cv_quality` maps bounding box center to quality grid cell, returns 0.5 fallback
- [ ] `_generate_low_confidence_explanation` returns `None` for `confidence >= 0.5`, string for below
- [ ] `_validate_template_fields` adds missing required fields as placeholders for known templates
- [ ] `_validate_template_fields` returns fields unchanged when `template_type is None`
- [ ] `postprocess_node` returns `enhanced_fields`, `comparison_data`, `audit_entries`
- [ ] `postprocess_node` audit entry has `step_name="postprocess"`, `step_order=3`
- [ ] `store_node` generates UUID `extraction_id` and sets `status="ready"`
- [ ] `store_node` calls `_persist_results` to write to DB
- [ ] `store_node` returns `status="error"` on DB failure
- [ ] `store_node` audit entry has `step_name="store"`, `step_order=4`
- [ ] All audit entries accumulate immutably
- [ ] All unit tests pass

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/library/pipeline/processing.py` | Modify | Add postprocess helpers, `postprocess_node`, `_persist_results`, `store_node` |
| `backend/tests/unit/library/pipeline/test_postprocess_node.py` | Create | Unit tests for postprocess_node and helpers |
| `backend/tests/unit/library/pipeline/test_store_node.py` | Create | Unit tests for store_node |

## Verification

```bash
# Run postprocess tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/pipeline/test_postprocess_node.py -v

# Run store tests
python -m pytest backend/tests/unit/library/pipeline/test_store_node.py -v

# Run all pipeline tests
python -m pytest backend/tests/unit/library/pipeline/ -v

# Run with coverage
python -m pytest backend/tests/unit/library/pipeline/ -v --cov=docmind.library.pipeline.processing --cov-report=term-missing

# Verify imports
python -c "from docmind.library.pipeline.processing import postprocess_node, store_node, _merge_confidence; print('OK')"
```
