"""Unit tests for extraction handler endpoints."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from docmind.modules.extractions.schemas import (
    AuditEntryResponse,
    ExtractionResponse,
    ExtractedFieldResponse,
    OverlayRegion,
    ComparisonResponse,
)


@pytest.fixture
def mock_extraction():
    return ExtractionResponse(
        id="ext-001",
        document_id="doc-001",
        mode="general",
        template_type=None,
        fields=[
            ExtractedFieldResponse(
                id="f1", field_type="key_value", field_key="total",
                field_value="$500", page_number=1,
                bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                confidence=0.9, vlm_confidence=0.95, cv_quality_score=0.8,
                is_required=False, is_missing=False,
            ),
        ],
        processing_time_ms=1200,
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )


class TestGetExtraction:

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.apiv1.handler.ExtractionUseCase")
    async def test_returns_extraction(self, MockUseCase, mock_extraction):
        from docmind.modules.extractions.apiv1.handler import get_extraction

        mock_uc = AsyncMock()
        mock_uc.get_extraction.return_value = mock_extraction
        MockUseCase.return_value = mock_uc

        result = await get_extraction("doc-001", current_user={"id": "u1"})

        assert result.id == "ext-001"
        mock_uc.get_extraction.assert_called_once_with(document_id="doc-001")

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.apiv1.handler.ExtractionUseCase")
    async def test_raises_404_when_not_found(self, MockUseCase):
        from docmind.shared.exceptions import NotFoundException
        from docmind.modules.extractions.apiv1.handler import get_extraction

        mock_uc = AsyncMock()
        mock_uc.get_extraction.side_effect = NotFoundException("Extraction not found")
        MockUseCase.return_value = mock_uc

        with pytest.raises(NotFoundException) as exc:
            await get_extraction("missing", current_user={"id": "u1"})

        assert exc.value.status_code == 404


class TestGetAuditTrail:

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.apiv1.handler.ExtractionUseCase")
    async def test_returns_audit_entries(self, MockUseCase):
        from docmind.modules.extractions.apiv1.handler import get_audit_trail

        entries = [AuditEntryResponse(
            step_name="preprocess", step_order=1,
            input_summary={}, output_summary={},
            parameters={}, duration_ms=100,
        )]
        mock_uc = AsyncMock()
        mock_uc.get_audit_trail.return_value = entries
        MockUseCase.return_value = mock_uc

        result = await get_audit_trail("doc-001", current_user={"id": "u1"})

        assert len(result) == 1
        assert result[0].step_name == "preprocess"


class TestGetOverlayData:

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.apiv1.handler.ExtractionUseCase")
    async def test_returns_overlay_regions(self, MockUseCase):
        from docmind.modules.extractions.apiv1.handler import get_overlay_data

        regions = [OverlayRegion(x=0.1, y=0.2, width=0.3, height=0.05, confidence=0.9, color="#22c55e", tooltip="total")]
        mock_uc = AsyncMock()
        mock_uc.get_overlay_data.return_value = regions
        MockUseCase.return_value = mock_uc

        result = await get_overlay_data("doc-001", current_user={"id": "u1"})

        assert len(result) == 1


class TestGetComparison:

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.apiv1.handler.ExtractionUseCase")
    async def test_returns_comparison(self, MockUseCase):
        from docmind.modules.extractions.apiv1.handler import get_comparison

        comp = ComparisonResponse(enhanced_fields=[], raw_fields=[], corrected=[], added=[])
        mock_uc = AsyncMock()
        mock_uc.get_comparison.return_value = comp
        MockUseCase.return_value = mock_uc

        result = await get_comparison("doc-001", current_user={"id": "u1"})

        assert result.corrected == []

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.apiv1.handler.ExtractionUseCase")
    async def test_raises_404_when_no_comparison(self, MockUseCase):
        from docmind.shared.exceptions import NotFoundException
        from docmind.modules.extractions.apiv1.handler import get_comparison

        mock_uc = AsyncMock()
        mock_uc.get_comparison.side_effect = NotFoundException("Comparison not available")
        MockUseCase.return_value = mock_uc

        with pytest.raises(NotFoundException) as exc:
            await get_comparison("missing", current_user={"id": "u1"})

        assert exc.value.status_code == 404
