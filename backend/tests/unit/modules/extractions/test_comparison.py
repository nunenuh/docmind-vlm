"""Unit tests for pipeline comparison: raw vs enhanced diff."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from docmind.modules.extractions.schemas import ComparisonResponse


class TestDiffFields:
    """Tests for ExtractionService.diff_fields."""

    def test_identifies_corrected_fields(self):
        from docmind.modules.extractions.services import ExtractionService

        raw = [
            {"field_key": "total", "page_number": 1, "field_value": "$500", "confidence": 0.9},
        ]
        enhanced = [
            {"id": "f1", "field_key": "total", "page_number": 1, "field_value": "$500", "confidence": 0.75},
        ]
        result = ExtractionService.diff_fields(enhanced, raw)

        assert "f1" in result["corrected"]
        assert "f1" not in result["added"]

    def test_identifies_added_fields(self):
        from docmind.modules.extractions.services import ExtractionService

        raw = [
            {"field_key": "total", "page_number": 1, "field_value": "$500", "confidence": 0.9},
        ]
        enhanced = [
            {"id": "f1", "field_key": "total", "page_number": 1, "field_value": "$500", "confidence": 0.9},
            {"id": "f2", "field_key": "vendor", "page_number": 1, "field_value": "Acme", "confidence": 0.0},
        ]
        result = ExtractionService.diff_fields(enhanced, raw)

        assert "f2" in result["added"]
        assert "f1" not in result["added"]

    def test_unchanged_fields_not_in_corrected_or_added(self):
        from docmind.modules.extractions.services import ExtractionService

        raw = [
            {"field_key": "total", "page_number": 1, "field_value": "$500", "confidence": 0.9},
        ]
        enhanced = [
            {"id": "f1", "field_key": "total", "page_number": 1, "field_value": "$500", "confidence": 0.9},
        ]
        result = ExtractionService.diff_fields(enhanced, raw)

        assert result["corrected"] == []
        assert result["added"] == []

    def test_value_change_marks_corrected(self):
        from docmind.modules.extractions.services import ExtractionService

        raw = [
            {"field_key": "date", "page_number": 1, "field_value": "2024-01-15", "confidence": 0.8},
        ]
        enhanced = [
            {"id": "f1", "field_key": "date", "page_number": 1, "field_value": "2024-01-16", "confidence": 0.8},
        ]
        result = ExtractionService.diff_fields(enhanced, raw)

        assert "f1" in result["corrected"]

    def test_empty_inputs(self):
        from docmind.modules.extractions.services import ExtractionService

        result = ExtractionService.diff_fields([], [])
        assert result["corrected"] == []
        assert result["added"] == []


class TestGetComparison:
    """Tests for ExtractionUseCase.get_comparison."""

    @pytest.mark.asyncio
    async def test_returns_comparison_response(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        mock_ext = MagicMock(id="ext-001")
        mock_field = MagicMock(
            id="f1",
            field_type="key_value",
            field_key="total",
            field_value="$500",
            page_number=1,
            bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            confidence=0.85,
            vlm_confidence=0.9,
            cv_quality_score=0.7,
            is_required=False,
            is_missing=False,
        )
        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_ext
        usecase.repo.get_fields.return_value = [mock_field]

        result = await usecase.get_comparison("doc-001")

        assert result is not None
        assert isinstance(result, ComparisonResponse)
        assert len(result.enhanced_fields) == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_no_extraction(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_comparison("nonexistent")
        assert result is None
