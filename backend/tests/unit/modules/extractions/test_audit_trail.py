"""Unit tests for audit trail retrieval through usecase."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from docmind.modules.extractions.schemas import AuditEntryResponse


@pytest.fixture
def mock_extraction_orm():
    ext = MagicMock()
    ext.id = "ext-001"
    ext.document_id = "doc-001"
    ext.mode = "general"
    ext.template_type = None
    ext.processing_time_ms = 1200
    ext.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    return ext


@pytest.fixture
def mock_audit_entries():
    entries = []
    for name, order, dur in [
        ("preprocess", 1, 350),
        ("extract", 2, 800),
        ("postprocess", 3, 150),
        ("store", 4, 50),
    ]:
        e = MagicMock()
        e.step_name = name
        e.step_order = order
        e.input_summary = {"step": name}
        e.output_summary = {"done": True}
        e.parameters = {}
        e.duration_ms = dur
        entries.append(e)
    return entries


class TestAuditTrailRetrieval:

    @pytest.mark.asyncio
    async def test_get_audit_trail_returns_ordered_entries(self, mock_extraction_orm, mock_audit_entries):
        from docmind.modules.extractions.usecases import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_audit_trail.return_value = mock_audit_entries

        result = await usecase.get_audit_trail("doc-001")

        assert len(result) == 4
        assert all(isinstance(r, AuditEntryResponse) for r in result)
        assert [r.step_name for r in result] == ["preprocess", "extract", "postprocess", "store"]
        assert [r.step_order for r in result] == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_get_audit_trail_empty_when_no_extraction(self):
        from docmind.modules.extractions.usecases import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_audit_trail("nonexistent-doc")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_audit_trail_empty_when_no_entries(self, mock_extraction_orm):
        from docmind.modules.extractions.usecases import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_audit_trail.return_value = []

        result = await usecase.get_audit_trail("doc-001")

        assert result == []
