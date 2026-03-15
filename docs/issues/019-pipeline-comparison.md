# Issue #19: Pipeline Comparison — Raw vs Enhanced

## Summary

Implement the pipeline comparison feature that stores raw VLM output as a baseline, diffs it against post-processed output, categorizes fields as corrected/added/unchanged, and serves the comparison via `GET /api/v1/extractions/{document_id}/comparison`. The comparison allows users to see exactly what the post-processing pipeline changed from the original VLM extraction.

## Context

- **Phase**: 4
- **Priority**: P1
- **Labels**: `phase-4-extraction`, `backend`, `tdd`
- **Dependencies**: #16 (extraction repository)
- **Branch**: `feat/19-pipeline-comparison`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/services.md` — ExtractionUseCase.get_comparison, ComparisonResponse
- `specs/backend/api.md` — ComparisonResponse schema
- `specs/backend/pipeline-processing.md` — postprocess node output structure

## Current State (Scaffold)

### `backend/src/docmind/modules/extractions/schemas.py` (ComparisonResponse -- already exists)
```python
class ComparisonResponse(BaseModel):
    enhanced_fields: list[ExtractedFieldResponse]
    raw_fields: list[dict]
    corrected: list[str]  # field IDs corrected by pipeline
    added: list[str]      # field IDs added by pipeline
```

### `backend/src/docmind/modules/extractions/usecase.py` (stub)
```python
class ExtractionUseCase:
    def get_comparison(self, document_id: str) -> ComparisonResponse | None:
        return None
```

## Requirements

### Functional

1. Create a `ComparisonService` (or add methods to `ExtractionService`) that:
   - `diff_fields(enhanced_fields, raw_fields)` compares enhanced vs raw field lists and categorizes each field ID as `corrected`, `added`, or `unchanged`.
   - A field is `corrected` if its `field_value` or `confidence` differs between raw and enhanced.
   - A field is `added` if it exists in enhanced but not in raw (matched by `field_key` + `page_number`).
   - A field is `unchanged` if values and confidence are identical.
2. `ExtractionUseCase.get_comparison(document_id)`:
   - Fetches the latest extraction and its fields (enhanced).
   - Fetches the audit trail and finds the `postprocess` step.
   - The `postprocess` step's `output_summary` contains `corrected_ids` and `added_ids` lists.
   - Builds `raw_fields` from enhanced fields by stripping pipeline enhancements: uses `vlm_confidence` as the raw confidence and excludes `added` fields.
   - Returns `ComparisonResponse`.
3. `GET /extractions/{document_id}/comparison` returns 404 if no extraction, otherwise the comparison.

### Non-Functional

- Comparison is computed on-the-fly, not stored separately.
- Raw fields use `vlm_confidence` (original VLM score) rather than the post-processed `confidence`.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/extractions/test_pipeline_comparison.py`

```python
"""Unit tests for pipeline comparison logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from docmind.modules.extractions.schemas import (
    ComparisonResponse,
    ExtractedFieldResponse,
)


def _make_field_response(
    id: str,
    field_key: str,
    field_value: str,
    confidence: float = 0.9,
    vlm_confidence: float = 0.85,
    page_number: int = 1,
) -> ExtractedFieldResponse:
    """Helper to create ExtractedFieldResponse."""
    return ExtractedFieldResponse(
        id=id,
        field_type="key_value",
        field_key=field_key,
        field_value=field_value,
        page_number=page_number,
        bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
        confidence=confidence,
        vlm_confidence=vlm_confidence,
        cv_quality_score=0.88,
        is_required=True,
        is_missing=False,
    )


class TestDiffFields:
    """Tests for the field diff algorithm."""

    def test_identifies_corrected_fields(self):
        from docmind.modules.extractions.services import ExtractionService

        service = ExtractionService()

        enhanced = [
            {"id": "f1", "field_key": "total", "field_value": "$1,500.00",
             "confidence": 0.95, "vlm_confidence": 0.70, "page_number": 1},
        ]
        raw = [
            {"id": "f1", "field_key": "total", "field_value": "$1,50.00",
             "confidence": 0.70, "page_number": 1},
        ]

        corrected, added = service.diff_fields(enhanced, raw)

        assert "f1" in corrected
        assert "f1" not in added

    def test_identifies_added_fields(self):
        from docmind.modules.extractions.services import ExtractionService

        service = ExtractionService()

        enhanced = [
            {"id": "f1", "field_key": "total", "field_value": "$1,500.00",
             "confidence": 0.95, "vlm_confidence": 0.90, "page_number": 1},
            {"id": "f2", "field_key": "tax", "field_value": "$150.00",
             "confidence": 0.85, "vlm_confidence": 0.0, "page_number": 1},
        ]
        raw = [
            {"id": "f1", "field_key": "total", "field_value": "$1,500.00",
             "confidence": 0.90, "page_number": 1},
        ]

        corrected, added = service.diff_fields(enhanced, raw)

        assert "f2" in added
        assert "f2" not in corrected

    def test_unchanged_fields_not_in_either_list(self):
        from docmind.modules.extractions.services import ExtractionService

        service = ExtractionService()

        enhanced = [
            {"id": "f1", "field_key": "vendor", "field_value": "Acme",
             "confidence": 0.90, "vlm_confidence": 0.90, "page_number": 1},
        ]
        raw = [
            {"id": "f1", "field_key": "vendor", "field_value": "Acme",
             "confidence": 0.90, "page_number": 1},
        ]

        corrected, added = service.diff_fields(enhanced, raw)

        assert "f1" not in corrected
        assert "f1" not in added

    def test_empty_inputs(self):
        from docmind.modules.extractions.services import ExtractionService

        service = ExtractionService()
        corrected, added = service.diff_fields([], [])

        assert corrected == []
        assert added == []


class TestGetComparison:
    """Tests for ExtractionUseCase.get_comparison."""

    @pytest.fixture
    def mock_extraction_orm(self):
        ext = MagicMock()
        ext.id = "ext-001"
        ext.document_id = "doc-001"
        ext.mode = "general"
        ext.template_type = None
        ext.processing_time_ms = 1200
        ext.created_at = datetime(2026, 1, 15, tzinfo=UTC)
        return ext

    @pytest.fixture
    def mock_fields_orm(self):
        f1 = MagicMock()
        f1.id = "f1"
        f1.field_type = "key_value"
        f1.field_key = "vendor_name"
        f1.field_value = "Acme Corp"
        f1.page_number = 1
        f1.bounding_box = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}
        f1.confidence = 0.92
        f1.vlm_confidence = 0.85
        f1.cv_quality_score = 0.88
        f1.is_required = True
        f1.is_missing = False
        return [f1]

    @pytest.fixture
    def mock_audit_with_postprocess(self):
        entry = MagicMock()
        entry.step_name = "postprocess"
        entry.step_order = 3
        entry.input_summary = {}
        entry.output_summary = {"corrected_ids": ["f1"], "added_ids": []}
        entry.parameters = {}
        entry.duration_ms = 100
        return [entry]

    @pytest.mark.asyncio
    async def test_returns_comparison_response(
        self, mock_extraction_orm, mock_fields_orm, mock_audit_with_postprocess
    ):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_fields.return_value = mock_fields_orm
        usecase.repo.get_audit_trail.return_value = mock_audit_with_postprocess

        result = await usecase.get_comparison("doc-001")

        assert result is not None
        assert isinstance(result, ComparisonResponse)
        assert len(result.enhanced_fields) == 1
        assert len(result.raw_fields) == 1
        assert result.corrected == ["f1"]
        assert result.added == []

    @pytest.mark.asyncio
    async def test_returns_none_when_no_extraction(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_comparison("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_raw_fields_use_vlm_confidence(
        self, mock_extraction_orm, mock_fields_orm, mock_audit_with_postprocess
    ):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_fields.return_value = mock_fields_orm
        usecase.repo.get_audit_trail.return_value = mock_audit_with_postprocess

        result = await usecase.get_comparison("doc-001")

        # Raw fields should use vlm_confidence as confidence
        assert result.raw_fields[0]["confidence"] == 0.85  # vlm_confidence, not 0.92

    @pytest.mark.asyncio
    async def test_added_fields_excluded_from_raw(self, mock_extraction_orm):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        f1 = MagicMock()
        f1.id = "f1"
        f1.field_type = "key_value"
        f1.field_key = "vendor"
        f1.field_value = "Acme"
        f1.page_number = 1
        f1.bounding_box = {}
        f1.confidence = 0.9
        f1.vlm_confidence = 0.9
        f1.cv_quality_score = 0.8
        f1.is_required = True
        f1.is_missing = False

        f2 = MagicMock()
        f2.id = "f2"
        f2.field_type = "key_value"
        f2.field_key = "tax"
        f2.field_value = "$50"
        f2.page_number = 1
        f2.bounding_box = {}
        f2.confidence = 0.7
        f2.vlm_confidence = 0.0
        f2.cv_quality_score = 0.0
        f2.is_required = False
        f2.is_missing = False

        audit_entry = MagicMock()
        audit_entry.step_name = "postprocess"
        audit_entry.step_order = 3
        audit_entry.output_summary = {"corrected_ids": [], "added_ids": ["f2"]}
        audit_entry.input_summary = {}
        audit_entry.parameters = {}
        audit_entry.duration_ms = 50

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_fields.return_value = [f1, f2]
        usecase.repo.get_audit_trail.return_value = [audit_entry]

        result = await usecase.get_comparison("doc-001")

        # f2 was added by pipeline, so raw_fields should only have f1
        raw_ids = [f["id"] for f in result.raw_fields]
        assert "f1" in raw_ids
        assert "f2" not in raw_ids
        assert result.added == ["f2"]
```

### Step 2: Implement (GREEN)

1. **`services.py`**: Add `diff_fields(enhanced, raw)` method that returns `(corrected_ids, added_ids)` by matching fields on `id` and comparing `field_value`/`confidence`.
2. **`usecase.py`**: Implement `get_comparison` as async method:
   - Fetch extraction + fields + audit trail
   - Find postprocess audit entry
   - Extract `corrected_ids` and `added_ids` from postprocess output_summary
   - Build raw_fields by converting fields (excluding added ones) and using `vlm_confidence`
   - Return `ComparisonResponse`

### Step 3: Refactor (IMPROVE)

- Move field-to-dict conversion to a shared helper.
- Ensure comparison gracefully handles missing postprocess audit entry (treat as no corrections).

## Acceptance Criteria

- [ ] `diff_fields` correctly identifies corrected, added, and unchanged fields
- [ ] `get_comparison` returns `ComparisonResponse` with enhanced_fields, raw_fields, corrected, added
- [ ] Raw fields use `vlm_confidence` (not post-processed `confidence`)
- [ ] Added fields (by pipeline) are excluded from raw_fields
- [ ] Returns `None` when no extraction exists
- [ ] Handles missing postprocess audit entry gracefully
- [ ] All unit tests pass

## Files Changed

- `backend/src/docmind/modules/extractions/services.py` — add `diff_fields`
- `backend/src/docmind/modules/extractions/usecase.py` — implement `get_comparison`
- `backend/tests/unit/modules/extractions/test_pipeline_comparison.py` — new

## Verification

```bash
cd backend
pytest tests/unit/modules/extractions/test_pipeline_comparison.py -v
```
