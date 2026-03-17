# Issue #16: Extraction Repository + UseCase

## Summary

Implement the `ExtractionRepository` with real SQLAlchemy async queries (`get_latest_extraction`, `get_fields`, `get_audit_trail`) and wire the `ExtractionUseCase` to orchestrate repository + service calls, returning properly constructed Pydantic response schemas. This issue replaces the current stub implementations with working database-backed logic.

## Context

- **Phase**: 4
- **Priority**: P0
- **Labels**: `phase-4-extraction`, `backend`, `tdd`
- **Dependencies**: #2 (Alembic migration), #14 (pipeline postprocess + store)
- **Branch**: `feat/16-extraction-repository`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/services.md` — ExtractionRepository and ExtractionUseCase spec
- `specs/backend/api.md` — ExtractionResponse, ExtractedFieldResponse, AuditEntryResponse schemas
- `specs/conventions/python-module-structure.md` — layer separation rules

## Current State (Scaffold)

### `backend/src/docmind/modules/extractions/repositories.py`
```python
"""docmind/modules/extractions/repositories.py — Stub."""
from docmind.core.logging import get_logger

logger = get_logger(__name__)


class ExtractionRepository:
    async def get_latest_extraction(self, document_id: str):
        raise NotImplementedError

    async def get_fields(self, extraction_id: str):
        raise NotImplementedError

    async def get_audit_trail(self, extraction_id: str):
        raise NotImplementedError
```

### `backend/src/docmind/modules/extractions/usecase.py`
```python
"""docmind/modules/extractions/usecase.py — Stub."""
from docmind.core.logging import get_logger
from .schemas import AuditEntryResponse, ComparisonResponse, ExtractionResponse, OverlayRegion

logger = get_logger(__name__)


class ExtractionUseCase:
    def get_extraction(self, document_id: str) -> ExtractionResponse | None:
        return None

    def get_audit_trail(self, document_id: str) -> list[AuditEntryResponse]:
        return []

    def get_overlay_data(self, document_id: str) -> list[OverlayRegion]:
        return []

    def get_comparison(self, document_id: str) -> ComparisonResponse | None:
        return None
```

## Requirements

### Functional

1. `ExtractionRepository.get_latest_extraction(document_id)` returns the most recent `Extraction` ORM record for a document, ordered by `created_at DESC`, or `None` if none exist.
2. `ExtractionRepository.get_fields(extraction_id)` returns all `ExtractedField` records for a given extraction, ordered by `page_number` then `field_key`.
3. `ExtractionRepository.get_audit_trail(extraction_id)` returns all `AuditEntry` records for a given extraction, ordered by `step_order`.
4. `ExtractionUseCase` instantiates `ExtractionRepository` and `ExtractionService`, delegates DB calls to the repo and business logic to the service.
5. `ExtractionUseCase.get_extraction(document_id)` fetches the latest extraction + its fields and returns an `ExtractionResponse` schema or `None`.
6. `ExtractionUseCase.get_audit_trail(document_id)` fetches the latest extraction, then its audit entries, and returns `list[AuditEntryResponse]`.
7. `ExtractionUseCase.get_overlay_data(document_id)` fetches fields and maps each through `ExtractionService.build_overlay_region`, returning `list[OverlayRegion]`.

### Non-Functional

- All repository methods are `async` and use `AsyncSessionLocal()` context manager.
- Repository returns ORM model instances; UseCase maps to Pydantic schemas.
- No business logic in the repository layer.
- No direct DB access in the UseCase layer.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/extractions/test_extraction_repository.py`

```python
"""Unit tests for ExtractionRepository with mocked async session."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC


@pytest.fixture
def mock_extraction():
    """Create a mock Extraction ORM object."""
    ext = MagicMock()
    ext.id = "ext-001"
    ext.document_id = "doc-001"
    ext.mode = "general"
    ext.template_type = None
    ext.processing_time_ms = 1200
    ext.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    return ext


@pytest.fixture
def mock_fields():
    """Create mock ExtractedField ORM objects."""
    field1 = MagicMock()
    field1.id = "field-001"
    field1.extraction_id = "ext-001"
    field1.field_type = "key_value"
    field1.field_key = "invoice_number"
    field1.field_value = "INV-2026-001"
    field1.page_number = 1
    field1.bounding_box = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}
    field1.confidence = 0.95
    field1.vlm_confidence = 0.92
    field1.cv_quality_score = 0.88
    field1.is_required = True
    field1.is_missing = False

    field2 = MagicMock()
    field2.id = "field-002"
    field2.extraction_id = "ext-001"
    field2.field_type = "key_value"
    field2.field_key = "total_amount"
    field2.field_value = "$1,500.00"
    field2.page_number = 1
    field2.bounding_box = {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05}
    field2.confidence = 0.85
    field2.vlm_confidence = 0.80
    field2.cv_quality_score = 0.90
    field2.is_required = True
    field2.is_missing = False

    return [field1, field2]


@pytest.fixture
def mock_audit_entries():
    """Create mock AuditEntry ORM objects."""
    entry1 = MagicMock()
    entry1.id = "audit-001"
    entry1.extraction_id = "ext-001"
    entry1.step_name = "preprocess"
    entry1.step_order = 1
    entry1.input_summary = {"file_type": "pdf", "file_size": 1024}
    entry1.output_summary = {"page_count": 2, "deskewed": True}
    entry1.parameters = {"dpi": 300}
    entry1.duration_ms = 350

    entry2 = MagicMock()
    entry2.id = "audit-002"
    entry2.extraction_id = "ext-001"
    entry2.step_name = "extract"
    entry2.step_order = 2
    entry2.input_summary = {"page_count": 2}
    entry2.output_summary = {"field_count": 5}
    entry2.parameters = {"provider": "dashscope", "model": "qwen-vl-max"}
    entry2.duration_ms = 800

    return [entry1, entry2]


class TestExtractionRepositoryGetLatestExtraction:
    """Tests for ExtractionRepository.get_latest_extraction."""

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_extraction_when_exists(self, mock_session_factory, mock_extraction):
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
        assert result.id == "ext-001"
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
    async def test_returns_audit_entries_ordered_by_step(self, mock_session_factory, mock_audit_entries):
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
        assert entries[0].step_order == 1
        assert entries[1].step_name == "extract"
        assert entries[1].step_order == 2

    @pytest.mark.asyncio
    @patch("docmind.modules.extractions.repositories.AsyncSessionLocal")
    async def test_returns_empty_list_when_no_audit_entries(self, mock_session_factory):
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


**Test file**: `backend/tests/unit/modules/extractions/test_extraction_usecase.py`

```python
"""Unit tests for ExtractionUseCase."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

from docmind.modules.extractions.schemas import (
    AuditEntryResponse,
    ExtractionResponse,
    ExtractedFieldResponse,
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
    ext.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
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
        assert result[0].color == "#22c55e"  # Green for confidence 0.92

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_extraction(self):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_overlay_data("nonexistent-doc")

        assert result == []
```

### Step 2: Implement (GREEN)

1. **`repositories.py`**: Replace stubs with real SQLAlchemy queries using `AsyncSessionLocal()`, `select()`, `.where()`, `.order_by()`, `.limit()` as shown in the spec.
2. **`usecase.py`**: Instantiate `ExtractionRepository` and `ExtractionService` in `__init__`. Make methods `async`. Call repo methods, map ORM objects to Pydantic schemas using attribute access (not dict access).

### Step 3: Refactor (IMPROVE)

- Extract ORM-to-schema mapping into private helper methods (e.g., `_to_field_response`, `_to_audit_response`).
- Add structlog context logging with `document_id` and `extraction_id`.
- Verify all methods handle the `None` case gracefully.

## Acceptance Criteria

- [ ] `ExtractionRepository.get_latest_extraction` queries DB and returns latest `Extraction` or `None`
- [ ] `ExtractionRepository.get_fields` returns ordered `ExtractedField` list
- [ ] `ExtractionRepository.get_audit_trail` returns ordered `AuditEntry` list
- [ ] `ExtractionUseCase.get_extraction` returns `ExtractionResponse` with nested fields
- [ ] `ExtractionUseCase.get_audit_trail` returns `list[AuditEntryResponse]`
- [ ] `ExtractionUseCase.get_overlay_data` returns `list[OverlayRegion]` via service
- [ ] All methods return empty/None when no data exists
- [ ] All unit tests pass (RED -> GREEN)
- [ ] No direct DB access in UseCase; no business logic in Repository

## Files Changed

- `backend/src/docmind/modules/extractions/repositories.py` — full implementation
- `backend/src/docmind/modules/extractions/usecase.py` — full implementation
- `backend/tests/unit/modules/extractions/test_extraction_repository.py` — new
- `backend/tests/unit/modules/extractions/test_extraction_usecase.py` — new

## Verification

```bash
cd backend
pytest tests/unit/modules/extractions/test_extraction_repository.py -v
pytest tests/unit/modules/extractions/test_extraction_usecase.py -v
pytest tests/unit/modules/extractions/ -v --tb=short
```
