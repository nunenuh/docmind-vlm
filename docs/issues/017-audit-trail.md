# Issue #17: Audit Trail Recording + Retrieval

## Summary

Implement audit trail recording during the processing pipeline and the retrieval endpoint. Each pipeline step (preprocess, extract, postprocess, store) records an `AuditEntry` with step metadata, timing, and input/output summaries. The GET `/api/v1/extractions/{document_id}/audit` endpoint returns the ordered timeline. This issue covers both the recording logic (called from pipeline nodes) and the retrieval path through the handler.

## Context

- **Phase**: 4
- **Priority**: P1
- **Labels**: `phase-4-extraction`, `backend`, `tdd`
- **Dependencies**: #14 (pipeline postprocess + store), #16 (extraction repository)
- **Branch**: `feat/17-audit-trail`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/services.md` — ExtractionRepository.get_audit_trail
- `specs/backend/api.md` — AuditEntryResponse schema, handler spec
- `specs/backend/pipeline-processing.md` — pipeline nodes that produce audit entries

## Current State (Scaffold)

### `backend/src/docmind/dbase/sqlalchemy/models.py` (AuditEntry model -- already exists)
```python
class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    extraction_id: Mapped[str] = mapped_column(String(36), ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(50), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    input_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    extraction: Mapped["Extraction"] = relationship(back_populates="audit_entries")
```

### `backend/src/docmind/modules/extractions/schemas.py` (AuditEntryResponse -- already exists)
```python
class AuditEntryResponse(BaseModel):
    step_name: str
    step_order: int
    input_summary: dict
    output_summary: dict
    parameters: dict
    duration_ms: int
```

### `backend/src/docmind/modules/extractions/apiv1/handler.py` (handler -- already exists, delegates to usecase)
```python
@router.get("/{document_id}/audit", response_model=list[AuditEntryResponse])
async def get_audit_trail(document_id: str, current_user: dict = Depends(get_current_user)):
    usecase = ExtractionUseCase()
    return usecase.get_audit_trail(document_id=document_id)
```

### `backend/src/docmind/modules/extractions/repositories.py` (stub)
```python
class ExtractionRepository:
    async def get_audit_trail(self, extraction_id: str):
        raise NotImplementedError
```

## Requirements

### Functional

1. Create an `AuditRecorder` utility class in `docmind/shared/audit.py` that:
   - Accepts an `extraction_id` at construction.
   - Provides a `record(step_name, step_order, input_summary, output_summary, parameters, duration_ms)` async method that inserts an `AuditEntry` row.
   - Provides a context manager `step(step_name, step_order, parameters)` that auto-times the step and records input/output summaries.
2. `ExtractionRepository.get_audit_trail(extraction_id)` returns `list[AuditEntry]` ordered by `step_order` ASC.
3. `ExtractionUseCase.get_audit_trail(document_id)` fetches the latest extraction, then its audit entries, maps to `list[AuditEntryResponse]`.
4. The handler at `GET /extractions/{document_id}/audit` returns the timeline. Empty list if no extraction exists.

### Non-Functional

- Audit recording must not block pipeline execution on failure (log warning and continue).
- `duration_ms` is measured with `time.perf_counter()` for accuracy.
- `input_summary` and `output_summary` are capped dicts (keys only, no large payloads).

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/shared/test_audit_recorder.py`

```python
"""Unit tests for AuditRecorder."""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch


class TestAuditRecorder:
    """Tests for the AuditRecorder utility."""

    @pytest.mark.asyncio
    @patch("docmind.shared.audit.async_session")
    async def test_record_creates_audit_entry(self, mock_session_factory):
        from docmind.shared.audit import AuditRecorder

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        recorder = AuditRecorder(extraction_id="ext-001")
        await recorder.record(
            step_name="preprocess",
            step_order=1,
            input_summary={"file_type": "pdf"},
            output_summary={"page_count": 3},
            parameters={"dpi": 300},
            duration_ms=450,
        )

        mock_session.add.assert_called_once()
        added_entry = mock_session.add.call_args[0][0]
        assert added_entry.extraction_id == "ext-001"
        assert added_entry.step_name == "preprocess"
        assert added_entry.step_order == 1
        assert added_entry.duration_ms == 450
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("docmind.shared.audit.async_session")
    async def test_record_does_not_raise_on_db_error(self, mock_session_factory):
        from docmind.shared.audit import AuditRecorder

        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("DB connection lost")
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        recorder = AuditRecorder(extraction_id="ext-001")

        # Should not raise -- logs warning instead
        await recorder.record(
            step_name="extract",
            step_order=2,
            input_summary={},
            output_summary={},
            parameters={},
            duration_ms=100,
        )

    @pytest.mark.asyncio
    @patch("docmind.shared.audit.async_session")
    async def test_step_context_manager_measures_duration(self, mock_session_factory):
        import asyncio
        from docmind.shared.audit import AuditRecorder

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        recorder = AuditRecorder(extraction_id="ext-001")

        async with recorder.step("preprocess", step_order=1, parameters={"dpi": 300}) as ctx:
            ctx.set_input({"file_type": "pdf"})
            await asyncio.sleep(0.05)  # Simulate work
            ctx.set_output({"page_count": 2})

        mock_session.add.assert_called_once()
        added_entry = mock_session.add.call_args[0][0]
        assert added_entry.step_name == "preprocess"
        assert added_entry.duration_ms >= 40  # At least ~50ms of sleep
        assert added_entry.input_summary == {"file_type": "pdf"}
        assert added_entry.output_summary == {"page_count": 2}
```

**Test file**: `backend/tests/unit/modules/extractions/test_audit_trail.py`

```python
"""Unit tests for audit trail retrieval through usecase."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from docmind.modules.extractions.schemas import AuditEntryResponse


@pytest.fixture
def mock_extraction_orm():
    ext = MagicMock()
    ext.id = "ext-001"
    ext.document_id = "doc-001"
    ext.mode = "general"
    ext.template_type = None
    ext.processing_time_ms = 1200
    ext.created_at = datetime(2026, 1, 15, tzinfo=UTC)
    return ext


@pytest.fixture
def mock_audit_entries():
    entries = []
    for i, (name, order, dur) in enumerate([
        ("preprocess", 1, 350),
        ("extract", 2, 800),
        ("postprocess", 3, 150),
        ("store", 4, 50),
    ]):
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
        from docmind.modules.extractions.usecase import ExtractionUseCase

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
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = None

        result = await usecase.get_audit_trail("nonexistent-doc")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_audit_trail_empty_when_no_entries(self, mock_extraction_orm):
        from docmind.modules.extractions.usecase import ExtractionUseCase

        usecase = ExtractionUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_latest_extraction.return_value = mock_extraction_orm
        usecase.repo.get_audit_trail.return_value = []

        result = await usecase.get_audit_trail("doc-001")

        assert result == []
```

### Step 2: Implement (GREEN)

1. **`shared/audit.py`**: Create `AuditRecorder` class with `record()` method and `step()` async context manager. Use `time.perf_counter()` for timing.
2. **`repositories.py`**: Implement `get_audit_trail` with SQLAlchemy query ordered by `step_order`.
3. **`usecase.py`**: Wire `get_audit_trail` through repo, map ORM to `AuditEntryResponse`.

### Step 3: Refactor (IMPROVE)

- Ensure `AuditRecorder.record` catches all exceptions and logs warnings.
- Add type hints for `StepContext` inner class used by the context manager.

## Acceptance Criteria

- [ ] `AuditRecorder.record()` inserts an `AuditEntry` row via SQLAlchemy
- [ ] `AuditRecorder.step()` context manager auto-measures `duration_ms`
- [ ] Audit recording failures are logged but never raise
- [ ] `ExtractionRepository.get_audit_trail` returns entries ordered by `step_order`
- [ ] `ExtractionUseCase.get_audit_trail` maps ORM entries to `AuditEntryResponse` schemas
- [ ] Empty list returned when no extraction or no entries exist
- [ ] All unit tests pass

## Files Changed

- `backend/src/docmind/shared/audit.py` — new file
- `backend/src/docmind/modules/extractions/repositories.py` — implement `get_audit_trail`
- `backend/src/docmind/modules/extractions/usecase.py` — implement `get_audit_trail`
- `backend/tests/unit/shared/test_audit_recorder.py` — new
- `backend/tests/unit/modules/extractions/test_audit_trail.py` — new

## Verification

```bash
cd backend
pytest tests/unit/shared/test_audit_recorder.py -v
pytest tests/unit/modules/extractions/test_audit_trail.py -v
```
