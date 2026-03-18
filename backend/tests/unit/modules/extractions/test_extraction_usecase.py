"""Unit tests for ExtractionUseCase."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from docmind.modules.extractions.schemas import (
    AuditEntryResponse,
    ExtractionResponse,
    OverlayRegion,
)


@pytest.fixture
def mock_extraction_orm():
    """Mock Extraction ORM object."""
    ext = MagicMock()
    ext.id = "ext-001"
    ext.document_id = "doc-001"
    ext.mode = "general"
    ext.template_type = None
    ext.processing_time_ms = 1200
    ext.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    return ext


@pytest.fixture
def mock_field_orm():
    """Mock ExtractedField ORM object."""
    field = MagicMock()
    field.id = "field-001"
    field.field_type = "key_value"
    field.field_key = "vendor_name"
    field.field_value = "Acme Corp"
    field.page_number = 1
    field.bounding_box = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}
    field.confidence = 0.92
    field.vlm_confidence = 0.90
    field.cv_quality_score = 0.88
    field.is_required = True
    field.is_missing = False
    return field


@pytest.fixture
def mock_audit_orm():
    """Mock AuditEntry ORM object."""
    entry = MagicMock()
    entry.step_name = "preprocess"
    entry.step_order = 1
    entry.input_summary = {"file_type": "pdf"}
    entry.output_summary = {"page_count": 2}
    entry.parameters = {"dpi": 300}
    entry.duration_ms = 350
    return entry


class TestExtractionUseCaseGetExtraction:
    """Tests for ExtractionUseCase.get_extraction."""

    @pytest.mark.asyncio
    async def test_returns_extraction_response_when_found(self, mock_extraction_orm, mock_field_orm):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_fields.return_value = [mock_field_orm]

        result = await usecase.get_extraction("doc-001")

        assert result is not None
        assert isinstance(result, ExtractionResponse)
        assert result.id == "ext-001"
        assert result.document_id == "doc-001"
        assert len(result.fields) == 1
        assert result.fields[0].field_key == "vendor_name"
        usecase.repo.get_latest_extraction.assert_called_once_with("doc-001")
        usecase.repo.get_fields.assert_called_once_with("ext-001")

    @pytest.mark.asyncio
    async def test_returns_none_when_no_extraction(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_extraction("nonexistent-doc")

        assert result is None
        usecase.repo.get_fields.assert_not_called()


class TestExtractionUseCaseGetAuditTrail:
    """Tests for ExtractionUseCase.get_audit_trail."""

    @pytest.mark.asyncio
    async def test_returns_audit_entries(self, mock_extraction_orm, mock_audit_orm):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_audit_trail.return_value = [mock_audit_orm]

        result = await usecase.get_audit_trail("doc-001")

        assert len(result) == 1
        assert isinstance(result[0], AuditEntryResponse)
        assert result[0].step_name == "preprocess"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_extraction(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_audit_trail("nonexistent-doc")

        assert result == []


class TestExtractionUseCaseGetOverlayData:
    """Tests for ExtractionUseCase.get_overlay_data."""

    @pytest.mark.asyncio
    async def test_returns_overlay_regions(self, mock_extraction_orm, mock_field_orm):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_fields.return_value = [mock_field_orm]

        result = await usecase.get_overlay_data("doc-001")

        assert len(result) == 1
        assert isinstance(result[0], OverlayRegion)
        assert result[0].confidence == 0.92
        # Green for high confidence
        assert result[0].color == "#22c55e"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_extraction(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_overlay_data("nonexistent-doc")

        assert result == []
