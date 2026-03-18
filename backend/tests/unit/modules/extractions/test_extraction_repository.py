"""Unit tests for ExtractionRepository."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_extraction():
    """Mock Extraction ORM object."""
    ext = MagicMock()
    ext.id = "ext-001"
    ext.document_id = "doc-001"
    ext.mode = "general"
    ext.template_type = None
    ext.processing_time_ms = 1200
    return ext


@pytest.fixture
def mock_fields():
    """Mock ExtractedField ORM objects."""
    f1 = MagicMock()
    f1.field_key = "invoice_number"
    f2 = MagicMock()
    f2.field_key = "total_amount"
    return [f1, f2]


@pytest.fixture
def mock_audit_entries():
    """Mock AuditEntry ORM objects."""
    e1 = MagicMock()
    e1.step_name = "preprocess"
    e1.step_order = 1
    e2 = MagicMock()
    e2.step_name = "extract"
    e2.step_order = 2
    return [e1, e2]


class TestExtractionRepositoryGetLatest:
    """Tests for ExtractionRepository.get_latest_extraction."""

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_latest_extraction(self, mock_session_factory, mock_extraction):
        from docmind.modules.extractions.repositories import ExtractionRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_extraction
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ExtractionRepository()
        result = await repo.get_latest_extraction("doc-001")

        assert result is not None
        assert result.document_id == "doc-001"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_none_when_no_extraction(self, mock_session_factory):
        from docmind.modules.extractions.repositories import ExtractionRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ExtractionRepository()
        result = await repo.get_latest_extraction("nonexistent-doc")

        assert result is None


class TestExtractionRepositoryGetFields:
    """Tests for ExtractionRepository.get_fields."""

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_fields_for_extraction(self, mock_session_factory, mock_fields):
        from docmind.modules.extractions.repositories import ExtractionRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_fields
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ExtractionRepository()
        fields = await repo.get_fields("ext-001")

        assert len(fields) == 2
        assert fields[0].field_key == "invoice_number"
        assert fields[1].field_key == "total_amount"

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_empty_list_when_no_fields(self, mock_session_factory):
        from docmind.modules.extractions.repositories import ExtractionRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ExtractionRepository()
        fields = await repo.get_fields("ext-nonexistent")

        assert fields == []


class TestExtractionRepositoryGetAuditTrail:
    """Tests for ExtractionRepository.get_audit_trail."""

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_audit_entries_ordered(self, mock_session_factory, mock_audit_entries):
        from docmind.modules.extractions.repositories import ExtractionRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_audit_entries
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ExtractionRepository()
        entries = await repo.get_audit_trail("ext-001")

        assert len(entries) == 2
        assert entries[0].step_name == "preprocess"
        assert entries[1].step_name == "extract"

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_empty_list_when_no_audit(self, mock_session_factory):
        from docmind.modules.extractions.repositories import ExtractionRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ExtractionRepository()
        entries = await repo.get_audit_trail("ext-nonexistent")

        assert entries == []
