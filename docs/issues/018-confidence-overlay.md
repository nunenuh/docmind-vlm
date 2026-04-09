# Issue #18: Confidence Overlay Generation

## Summary

Implement confidence overlay generation that maps extracted field confidence scores to colored bounding box regions for document visualization. The `ExtractionService` already has `confidence_color` and `build_overlay_region` static methods implemented. This issue wires the full path: repository fetches fields, service generates overlay regions, usecase returns `list[OverlayRegion]`, and the handler serves `GET /extractions/{document_id}/overlay`.

## Context

- **Phase**: 4
- **Priority**: P1
- **Labels**: `phase-4-extraction`, `backend`, `tdd`
- **Dependencies**: #16 (extraction repository)
- **Branch**: `feat/18-confidence-overlay`
- **Estimated scope**: S

## Specs to Read

- `specs/backend/services.md` — ExtractionService.confidence_color, build_overlay_region
- `specs/backend/api.md` — OverlayRegion schema, overlay endpoint

## Current State (Scaffold)

### `backend/src/docmind/modules/extractions/services.py` (already implemented)
```python
"""docmind/modules/extractions/services.py"""
from docmind.core.logging import get_logger

logger = get_logger(__name__)

COLOR_HIGH = "#22c55e"
COLOR_MEDIUM = "#eab308"
COLOR_LOW = "#ef4444"


class ExtractionService:
    @staticmethod
    def confidence_color(confidence: float) -> str:
        if confidence >= 0.8:
            return COLOR_HIGH
        if confidence >= 0.5:
            return COLOR_MEDIUM
        return COLOR_LOW

    @staticmethod
    def build_overlay_region(field: dict) -> dict | None:
        bbox = field.get("bounding_box", {})
        if not bbox or not bbox.get("x"):
            return None
        confidence = field.get("confidence", 0.0)
        field_key = field.get("field_key", "")
        field_value = field.get("field_value", "")
        tooltip = f"{field_key}: {field_value}" if field_key else field_value
        return {
            "x": bbox["x"], "y": bbox["y"], "width": bbox["width"], "height": bbox["height"],
            "confidence": confidence, "color": ExtractionService.confidence_color(confidence),
            "tooltip": tooltip[:200],
        }
```

### `backend/src/docmind/modules/extractions/schemas.py` (OverlayRegion -- already exists)
```python
class OverlayRegion(BaseModel):
    x: float
    y: float
    width: float
    height: float
    confidence: float
    color: str
    tooltip: str | None
```

### `backend/src/docmind/modules/extractions/usecase.py` (stub)
```python
class ExtractionUseCase:
    def get_overlay_data(self, document_id: str) -> list[OverlayRegion]:
        return []
```

## Requirements

### Functional

1. `ExtractionService.confidence_color` maps scores: green (`#22c55e`) for >= 0.8, yellow (`#eab308`) for >= 0.5, red (`#ef4444`) for < 0.5.
2. `ExtractionService.build_overlay_region` converts an extracted field dict to an overlay region dict, or returns `None` if no bounding box data.
3. `ExtractionUseCase.get_overlay_data` fetches latest extraction, gets its fields, maps each through `build_overlay_region`, filters `None`, returns `list[OverlayRegion]`.
4. Tooltip is `"{field_key}: {field_value}"` if key exists, otherwise just `field_value`, truncated to 200 chars.
5. Fields without bounding box data (missing `x` key) are excluded from overlay.

### Non-Functional

- Color mapping is deterministic and consistent.
- Boundary values are tested: exactly 0.8, exactly 0.5, 0.0, 1.0.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/extractions/test_confidence_overlay.py`

```python
"""Unit tests for confidence overlay generation."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from docmind.modules.extractions.services import ExtractionService, COLOR_HIGH, COLOR_MEDIUM, COLOR_LOW
from docmind.modules.extractions.schemas import OverlayRegion


# ─────────────────────────────────────────────
# ExtractionService.confidence_color tests
# ─────────────────────────────────────────────

class TestConfidenceColor:

    def test_high_confidence_returns_green(self):
        assert ExtractionService.confidence_color(0.95) == COLOR_HIGH
        assert ExtractionService.confidence_color(0.99) == COLOR_HIGH

    def test_boundary_0_8_returns_green(self):
        assert ExtractionService.confidence_color(0.8) == COLOR_HIGH

    def test_medium_confidence_returns_yellow(self):
        assert ExtractionService.confidence_color(0.65) == COLOR_MEDIUM
        assert ExtractionService.confidence_color(0.79) == COLOR_MEDIUM

    def test_boundary_0_5_returns_yellow(self):
        assert ExtractionService.confidence_color(0.5) == COLOR_MEDIUM

    def test_low_confidence_returns_red(self):
        assert ExtractionService.confidence_color(0.3) == COLOR_LOW
        assert ExtractionService.confidence_color(0.1) == COLOR_LOW

    def test_zero_confidence_returns_red(self):
        assert ExtractionService.confidence_color(0.0) == COLOR_LOW

    def test_boundary_0_49_returns_red(self):
        assert ExtractionService.confidence_color(0.49) == COLOR_LOW

    def test_max_confidence_returns_green(self):
        assert ExtractionService.confidence_color(1.0) == COLOR_HIGH


# ─────────────────────────────────────────────
# ExtractionService.build_overlay_region tests
# ─────────────────────────────────────────────

class TestBuildOverlayRegion:

    def test_builds_region_with_valid_bbox(self):
        field = {
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            "confidence": 0.92,
            "field_key": "vendor_name",
            "field_value": "Acme Corp",
        }
        result = ExtractionService.build_overlay_region(field)

        assert result is not None
        assert result["x"] == 0.1
        assert result["y"] == 0.2
        assert result["width"] == 0.3
        assert result["height"] == 0.05
        assert result["confidence"] == 0.92
        assert result["color"] == COLOR_HIGH
        assert result["tooltip"] == "vendor_name: Acme Corp"

    def test_returns_none_for_empty_bbox(self):
        field = {
            "bounding_box": {},
            "confidence": 0.9,
            "field_key": "test",
            "field_value": "value",
        }
        result = ExtractionService.build_overlay_region(field)
        assert result is None

    def test_returns_none_for_missing_bbox(self):
        field = {
            "confidence": 0.9,
            "field_key": "test",
            "field_value": "value",
        }
        result = ExtractionService.build_overlay_region(field)
        assert result is None

    def test_returns_none_for_bbox_without_x(self):
        field = {
            "bounding_box": {"y": 0.2, "width": 0.3, "height": 0.05},
            "confidence": 0.9,
            "field_key": "test",
            "field_value": "value",
        }
        result = ExtractionService.build_overlay_region(field)
        assert result is None

    def test_tooltip_without_field_key(self):
        field = {
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            "confidence": 0.6,
            "field_key": "",
            "field_value": "some text block",
        }
        result = ExtractionService.build_overlay_region(field)
        assert result is not None
        assert result["tooltip"] == "some text block"

    def test_tooltip_truncated_to_200_chars(self):
        long_value = "x" * 300
        field = {
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            "confidence": 0.9,
            "field_key": "key",
            "field_value": long_value,
        }
        result = ExtractionService.build_overlay_region(field)
        assert result is not None
        assert len(result["tooltip"]) == 200

    def test_low_confidence_field_gets_red_color(self):
        field = {
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            "confidence": 0.3,
            "field_key": "total",
            "field_value": "$100",
        }
        result = ExtractionService.build_overlay_region(field)
        assert result is not None
        assert result["color"] == COLOR_LOW


# ─────────────────────────────────────────────
# ExtractionUseCase.get_overlay_data tests
# ─────────────────────────────────────────────

class TestGetOverlayData:

    @pytest.mark.asyncio
    async def test_returns_overlay_regions_for_fields_with_bbox(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        mock_ext = MagicMock()
        mock_ext.id = "ext-001"

        mock_field1 = MagicMock()
        mock_field1.id = "f1"
        mock_field1.bounding_box = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}
        mock_field1.confidence = 0.9
        mock_field1.field_key = "vendor"
        mock_field1.field_value = "Acme"

        mock_field2 = MagicMock()
        mock_field2.id = "f2"
        mock_field2.bounding_box = {}  # No bbox -- should be excluded
        mock_field2.confidence = 0.8
        mock_field2.field_key = "date"
        mock_field2.field_value = "2026-01-01"

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_ext
        usecase.repo.get_fields.return_value = [mock_field1, mock_field2]

        result = await usecase.get_overlay_data("doc-001")

        assert len(result) == 1  # Only field1 has valid bbox
        assert isinstance(result[0], OverlayRegion)
        assert result[0].color == COLOR_HIGH

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_extraction(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_overlay_data("nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_fields_have_bbox(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        mock_ext = MagicMock()
        mock_ext.id = "ext-001"

        mock_field = MagicMock()
        mock_field.bounding_box = {}
        mock_field.confidence = 0.9
        mock_field.field_key = "test"
        mock_field.field_value = "val"

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_ext
        usecase.repo.get_fields.return_value = [mock_field]

        result = await usecase.get_overlay_data("doc-001")

        assert result == []
```

### Step 2: Implement (GREEN)

1. The `ExtractionService` methods are already implemented. Verify they work with the tests.
2. Implement `ExtractionUseCase.get_overlay_data` as an async method that:
   - Calls `self.repo.get_latest_extraction(document_id)`
   - If None, returns `[]`
   - Calls `self.repo.get_fields(extraction.id)`
   - For each field, converts ORM attributes to a dict and calls `self.service.build_overlay_region(field_dict)`
   - Filters `None` results and wraps in `OverlayRegion` schemas

### Step 3: Refactor (IMPROVE)

- Extract field-ORM-to-dict conversion into a shared helper.
- Ensure consistent dict key names between ORM attributes and `build_overlay_region` expectations.

## Acceptance Criteria

- [ ] `confidence_color` correctly maps all boundary values (0.0, 0.49, 0.5, 0.79, 0.8, 1.0)
- [ ] `build_overlay_region` returns `None` for fields without valid bounding box
- [ ] `build_overlay_region` truncates tooltip to 200 characters
- [ ] `get_overlay_data` returns only fields with valid bounding boxes
- [ ] `get_overlay_data` returns empty list when no extraction exists
- [ ] All unit tests pass

## Files Changed

- `backend/src/docmind/modules/extractions/usecase.py` — implement `get_overlay_data`
- `backend/tests/unit/modules/extractions/test_confidence_overlay.py` — new

## Verification

```bash
cd backend
pytest tests/unit/modules/extractions/test_confidence_overlay.py -v
```
