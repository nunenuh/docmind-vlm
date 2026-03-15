# Issue #11: Pipeline Preprocess Node

## Summary

Implement the `preprocess_node` LangGraph node function in `backend/src/docmind/library/pipeline/processing.py`. This node takes raw file bytes and metadata from the `ProcessingState`, runs CV preprocessing (convert to page images, deskew, quality assessment), and outputs updated state with `page_images`, `quality_map`, `skew_angles`, `page_count`, and an audit entry. It also invokes the optional `progress_callback` at each substep.

## Context
- **Phase**: 3 — Processing Pipeline
- **Priority**: P0
- **Labels**: `phase-3-pipeline`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: None (CV library functions already implemented)
- **Branch**: `feat/11-pipeline-preprocess`
- **Estimated scope**: M

## Specs to Read
- `specs/backend/pipeline-processing.md` — Full preprocess node spec, state schema, audit entry format
- `specs/backend/cv.md` — CV module functions: `convert_to_page_images`, `detect_and_correct`, `assess_regions`
- `specs/conventions/python-module-structure.md` — Layer rules (pipeline is library-level, no module imports)

## Current State (Scaffold)

**`backend/src/docmind/library/pipeline/processing.py`** — Contains `ProcessingState` and `AuditEntry` TypedDicts, but `run_processing_pipeline` is a stub:

```python
"""
docmind/library/pipeline/processing.py

LangGraph StateGraph for the document processing pipeline.
Stub implementation for scaffold.
"""
import logging
from typing import Any, Callable, TypedDict

logger = logging.getLogger(__name__)


class AuditEntry(TypedDict):
    step_name: str
    step_order: int
    input_summary: dict
    output_summary: dict
    parameters: dict
    duration_ms: int
    timestamp: str


class ProcessingState(TypedDict):
    document_id: str
    user_id: str
    file_bytes: bytes
    file_type: str
    template_type: str | None
    page_images: list[Any]
    page_count: int
    quality_map: dict
    skew_angles: list[float]
    raw_fields: list[dict]
    vlm_response: dict
    document_type: str | None
    enhanced_fields: list[dict]
    comparison_data: dict
    extraction_id: str
    status: str
    error_message: str | None
    audit_entries: list[AuditEntry]
    progress_callback: Callable | None


def run_processing_pipeline(initial_state: dict) -> dict:
    """
    Run the full processing pipeline.
    Stub implementation — raises NotImplementedError.
    """
    raise NotImplementedError("Processing pipeline not yet implemented")
```

**CV library functions already implemented:**

- `docmind.library.cv.preprocessing.convert_to_page_images(file_bytes, file_type)` -> `list[np.ndarray]`
- `docmind.library.cv.deskew.detect_and_correct(image, threshold=2.0)` -> `tuple[np.ndarray, float]`
- `docmind.library.cv.quality.assess_regions(image, grid_rows=4, grid_cols=4)` -> `dict[tuple[int,int], RegionQuality]`
- `RegionQuality` is a frozen dataclass with `blur_score`, `noise_score`, `contrast_score`, `overall_score`

## Requirements

### Functional

1. `preprocess_node(state: dict) -> dict` is a pure function that reads `file_bytes` and `file_type` from state.
2. Step 1: Call `convert_to_page_images(file_bytes, file_type)` to get raw page images.
3. Step 2: Iterate pages, call `detect_and_correct(page_img)` on each. Collect corrected images and skew angles.
4. Step 3: Call `assess_regions(corrected_images[0])` on the first page to produce the quality map.
5. Serialize quality map keys from `(row, col)` tuples to `"row,col"` strings. Serialize `RegionQuality` dataclass to dict with keys `blur_score`, `noise_score`, `contrast_score`, `overall_score`.
6. Build an `AuditEntry` dict with `step_name="preprocess"`, `step_order=1`, input/output summaries, parameters, and `duration_ms`.
7. Return state updates: `page_images`, `page_count`, `quality_map`, `skew_angles`, `audit_entries` (appended).
8. On exception, return `{"status": "error", "error_message": "Preprocessing failed: {e}"}`.
9. If `progress_callback` is present in state, call it at each substep with `(step, progress, message)`.

### Non-Functional

- Must not mutate the input `state` dict. Return new dicts only.
- Must not import from `docmind.modules.*`.
- Duration measured with `time.time()` in milliseconds.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/pipeline/test_preprocess_node.py`

```python
"""
Unit tests for the preprocess_node pipeline function.

All CV library functions are mocked — these tests verify
state transitions, audit entry creation, callback invocation,
and error handling.
"""
import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch, call
import numpy as np


@dataclass(frozen=True)
class FakeRegionQuality:
    blur_score: float
    noise_score: float
    contrast_score: float
    overall_score: float


def _make_state(
    file_bytes: bytes = b"fake-pdf-bytes",
    file_type: str = "pdf",
    callback: object | None = None,
) -> dict:
    """Build a minimal ProcessingState dict for preprocess_node."""
    return {
        "document_id": "doc-123",
        "user_id": "user-456",
        "file_bytes": file_bytes,
        "file_type": file_type,
        "template_type": None,
        "page_images": [],
        "page_count": 0,
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


class TestPreprocessNodeHappyPath:
    """Tests for successful preprocessing."""

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_page_images_and_count(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """preprocess_node returns corrected images and page count."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img, fake_img]
        mock_deskew.side_effect = [(fake_img, 0.5), (fake_img, -1.2)]
        mock_quality.return_value = {
            (0, 0): FakeRegionQuality(10.0, 5.0, 40.0, 0.75),
        }

        state = _make_state()
        result = preprocess_node(state)

        assert len(result["page_images"]) == 2
        assert result["page_count"] == 2

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_skew_angles(self, mock_convert, mock_deskew, mock_quality):
        """preprocess_node collects skew angles from each page."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 3.14)
        mock_quality.return_value = {}

        state = _make_state()
        result = preprocess_node(state)

        assert result["skew_angles"] == [3.14]

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_serializes_quality_map(self, mock_convert, mock_deskew, mock_quality):
        """Quality map keys are serialized from tuples to 'row,col' strings."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {
            (0, 0): FakeRegionQuality(10.0, 5.0, 40.0, 0.8),
            (1, 2): FakeRegionQuality(20.0, 8.0, 50.0, 0.6),
        }

        state = _make_state()
        result = preprocess_node(state)

        assert "0,0" in result["quality_map"]
        assert "1,2" in result["quality_map"]
        assert result["quality_map"]["0,0"]["overall_score"] == 0.8
        assert result["quality_map"]["1,2"]["blur_score"] == 20.0

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_creates_audit_entry(self, mock_convert, mock_deskew, mock_quality):
        """preprocess_node appends an audit entry with step_name='preprocess'."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        state = _make_state()
        result = preprocess_node(state)

        assert len(result["audit_entries"]) == 1
        entry = result["audit_entries"][0]
        assert entry["step_name"] == "preprocess"
        assert entry["step_order"] == 1
        assert "file_type" in entry["input_summary"]
        assert "page_count" in entry["output_summary"]
        assert isinstance(entry["duration_ms"], int)
        assert entry["duration_ms"] >= 0

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_appends_to_existing_audit_entries(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """Audit entries accumulate; existing entries are preserved."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        existing_entry = {"step_name": "init", "step_order": 0}
        state = _make_state()
        state["audit_entries"] = [existing_entry]
        result = preprocess_node(state)

        assert len(result["audit_entries"]) == 2
        assert result["audit_entries"][0]["step_name"] == "init"
        assert result["audit_entries"][1]["step_name"] == "preprocess"

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_does_not_set_error_status_on_success(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """On success, result should NOT contain status='error'."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        state = _make_state()
        result = preprocess_node(state)

        assert result.get("status") != "error"


class TestPreprocessNodeCallback:
    """Tests for progress callback invocation."""

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_callback_invoked_at_each_substep(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """progress_callback is called with step='preprocess' at multiple progress points."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        callback = MagicMock()
        state = _make_state(callback=callback)
        preprocess_node(state)

        assert callback.call_count >= 3
        for c in callback.call_args_list:
            assert c.kwargs.get("step") == "preprocess" or c[1].get("step") == "preprocess" or c[0][0] == "preprocess" if c[0] else True

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_works_without_callback(self, mock_convert, mock_deskew, mock_quality):
        """preprocess_node works fine when progress_callback is None."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        state = _make_state(callback=None)
        result = preprocess_node(state)

        assert result["page_count"] == 1


class TestPreprocessNodeErrorHandling:
    """Tests for error cases."""

    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_error_on_conversion_failure(self, mock_convert):
        """If convert_to_page_images raises, returns status='error'."""
        from docmind.library.pipeline.processing import preprocess_node

        mock_convert.side_effect = ValueError("Unsupported file type: xyz")

        state = _make_state(file_type="xyz")
        result = preprocess_node(state)

        assert result["status"] == "error"
        assert "Preprocessing failed" in result["error_message"]

    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_error_on_deskew_failure(self, mock_convert, mock_deskew):
        """If detect_and_correct raises, returns status='error'."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.side_effect = RuntimeError("Deskew failed")

        state = _make_state()
        result = preprocess_node(state)

        assert result["status"] == "error"
        assert "Preprocessing failed" in result["error_message"]

    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_handles_empty_file_bytes(self, mock_convert):
        """Empty file bytes should propagate as an error."""
        from docmind.library.pipeline.processing import preprocess_node

        mock_convert.side_effect = ValueError("PDF bytes cannot be empty")

        state = _make_state(file_bytes=b"")
        result = preprocess_node(state)

        assert result["status"] == "error"


class TestPreprocessNodeQualityMapEdgeCases:
    """Tests for quality map edge cases."""

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_empty_quality_map_when_no_images(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """If no corrected images, quality_map should be empty."""
        from docmind.library.pipeline.processing import preprocess_node

        mock_convert.return_value = []

        state = _make_state()
        result = preprocess_node(state)

        assert result["quality_map"] == {}
        assert result["page_count"] == 0

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_mean_quality_in_audit_with_regions(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """Audit output_summary includes mean_quality computed from quality_map."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {
            (0, 0): FakeRegionQuality(10.0, 5.0, 40.0, 0.8),
            (0, 1): FakeRegionQuality(10.0, 5.0, 40.0, 0.6),
        }

        state = _make_state()
        result = preprocess_node(state)

        audit = result["audit_entries"][-1]
        expected_mean = (0.8 + 0.6) / 2
        assert abs(audit["output_summary"]["mean_quality"] - expected_mean) < 0.01
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/pipeline/processing.py`

**Implementation guidance**:

1. Add imports at the top of `processing.py`:
   ```python
   import time
   from docmind.library.cv.preprocessing import convert_to_page_images
   from docmind.library.cv.deskew import detect_and_correct
   from docmind.library.cv.quality import assess_regions
   ```

2. Implement `preprocess_node(state: dict) -> dict` exactly as specified in `specs/backend/pipeline-processing.md`:
   - Start timer with `time.time()`
   - Get `progress_callback` from state, check before calling
   - Call `convert_to_page_images(file_bytes, file_type)`
   - Loop pages: call `detect_and_correct(page_img)`, collect corrected images and angles
   - If corrected images exist, call `assess_regions(corrected_images[0])`
   - Serialize quality map: tuple keys -> `"row,col"` strings, `RegionQuality` -> dict
   - Build audit entry dict
   - Return state update dict (new dict, no mutation)
   - Wrap in try/except, return error state on failure

3. Do NOT yet implement `extract_node`, `postprocess_node`, `store_node`, or `build_processing_graph`. Keep those as stubs or leave `run_processing_pipeline` raising `NotImplementedError` for now.

### Step 3: Refactor (IMPROVE)
- Extract quality map serialization into a private `_serialize_quality_map()` helper
- Ensure all numeric values are JSON-serializable (no numpy types leaking)
- Verify no mutation of input state

## Acceptance Criteria
- [ ] `preprocess_node` function exists and is importable from `docmind.library.pipeline.processing`
- [ ] Takes `state: dict` and returns `dict` with keys: `page_images`, `page_count`, `quality_map`, `skew_angles`, `audit_entries`
- [ ] Calls `convert_to_page_images`, `detect_and_correct`, `assess_regions` from library/cv
- [ ] Quality map serialized with string keys and dict values
- [ ] Audit entry has `step_name="preprocess"`, `step_order=1`, `duration_ms` as int
- [ ] Appends to existing `audit_entries` (immutable pattern)
- [ ] Returns `status="error"` with `error_message` on any exception
- [ ] Invokes `progress_callback` at each substep when present, skips when None
- [ ] All unit tests pass with mocked CV functions
- [ ] No imports from `docmind.modules.*`

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/library/pipeline/processing.py` | Modify | Add `preprocess_node` function with CV imports |
| `backend/tests/unit/library/pipeline/test_preprocess_node.py` | Create | Unit tests for preprocess_node |
| `backend/tests/unit/library/__init__.py` | Create | Empty `__init__.py` for test package |
| `backend/tests/unit/library/pipeline/__init__.py` | Create | Empty `__init__.py` for test package |

## Verification

```bash
# Run just the preprocess node tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/pipeline/test_preprocess_node.py -v

# Run with coverage
python -m pytest backend/tests/unit/library/pipeline/test_preprocess_node.py -v --cov=docmind.library.pipeline.processing --cov-report=term-missing

# Verify import works
python -c "from docmind.library.pipeline.processing import preprocess_node; print('OK')"
```
