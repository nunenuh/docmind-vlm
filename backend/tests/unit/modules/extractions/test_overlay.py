"""Unit tests for confidence overlay generation."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from docmind.modules.extractions.schemas import OverlayRegion
from docmind.modules.extractions.services import ExtractionService


class TestExtractionServiceConfidenceColor:
    """Tests for ExtractionService.confidence_color."""

    def test_high_confidence_returns_green(self):
        service = ExtractionService()
        assert service.confidence_color(0.95) == "#22c55e"
        assert service.confidence_color(0.80) == "#22c55e"

    def test_medium_confidence_returns_amber(self):
        service = ExtractionService()
        assert service.confidence_color(0.79) == "#eab308"
        assert service.confidence_color(0.50) == "#eab308"

    def test_low_confidence_returns_red(self):
        service = ExtractionService()
        assert service.confidence_color(0.49) == "#ef4444"
        assert service.confidence_color(0.0) == "#ef4444"


class TestExtractionServiceBuildOverlayRegion:
    """Tests for ExtractionService.build_overlay_region."""

    def test_builds_region_from_field(self):
        service = ExtractionService()
        field = {
            "field_key": "total",
            "field_value": "$500",
            "confidence": 0.9,
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
        }
        region = service.build_overlay_region(field)
        assert region is not None
        assert region["x"] == 0.1
        assert region["confidence"] == 0.9
        assert region["color"] == "#22c55e"
        assert "total" in region["tooltip"]

    def test_returns_none_for_empty_bbox(self):
        service = ExtractionService()
        field = {"confidence": 0.9, "bounding_box": {}}
        assert service.build_overlay_region(field) is None

    def test_returns_none_for_missing_bbox(self):
        service = ExtractionService()
        field = {"confidence": 0.9}
        assert service.build_overlay_region(field) is None


class TestOverlayDataUsecase:
    """Tests for ExtractionUseCase.get_overlay_data."""

    @pytest.mark.asyncio
    async def test_returns_overlay_regions_with_colors(self):
        from docmind.modules.extractions.usecases import ExtractionUseCase

        mock_ext = MagicMock(id="ext-001")
        mock_field = MagicMock(
            bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            confidence=0.45,
            field_key="amount",
            field_value="$100",
        )
        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_ext
        usecase.repo.get_fields.return_value = [mock_field]

        result = await usecase.get_overlay_data("doc-001")

        assert len(result) == 1
        assert isinstance(result[0], OverlayRegion)
        assert result[0].color == "#ef4444"  # red for low confidence

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_extraction(self):
        from docmind.modules.extractions.usecases import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_overlay_data("nonexistent")
        assert result == []
