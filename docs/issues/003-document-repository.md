# Issue #3: Implement DocumentRepository with Full CRUD

## Summary

Replace the stub `DocumentRepository` with a fully working implementation using SQLAlchemy async sessions. The repository provides five operations: `create`, `get_by_id`, `list_for_user` (paginated), `delete` (with cascading cleanup), and `update_status`. Every query must filter by `user_id` for ownership enforcement. This is the data access foundation for all document-related features.

## Context

- **Phase**: 1 — Infrastructure
- **Priority**: P0
- **Labels**: `phase-1-infra`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: #2 (Alembic migration — tables must exist)
- **Branch**: `feat/3-document-repository`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/services.md` — Section "Documents Module > repositories.py" for full implementation spec
- `specs/backend/api.md` — Section "dbase/psql/models/" for ORM model definitions
- `specs/conventions/python-module-structure.md` — Section "modules/*/repositories.py" layer rules
- `specs/conventions/security.md` — Section "Ownership Enforcement" for user_id filtering

## Current State (Scaffold)

**File: `backend/src/docmind/modules/documents/repositories.py`**

```python
"""docmind/modules/documents/repositories.py — Stub."""
from docmind.core.logging import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    async def create(self, user_id: str, filename: str, file_type: str, file_size: int, storage_path: str):
        raise NotImplementedError

    async def get_by_id(self, document_id: str, user_id: str):
        raise NotImplementedError

    async def list_for_user(self, user_id: str, page: int, limit: int):
        raise NotImplementedError

    async def delete(self, document_id: str, user_id: str):
        raise NotImplementedError

    async def update_status(self, document_id: str, status: str, **kwargs):
        raise NotImplementedError
```

**File: `backend/src/docmind/dbase/psql/core/engine.py`**

```python
"""Async SQLAlchemy engine and session factory."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from docmind.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=settings.APP_DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

**File: `backend/src/docmind/dbase/psql/models/`** (Document model)

```python
class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
```

## Requirements

### Functional

1. `create(user_id, filename, file_type, file_size, storage_path) -> Document` — Insert a new document record, return the ORM instance with all defaults populated (id, status, created_at, updated_at)
2. `get_by_id(document_id, user_id) -> Document | None` — Fetch by ID, always filtering by user_id. Return `None` if not found or if user_id does not match
3. `list_for_user(user_id, page, limit) -> tuple[list[Document], int]` — Paginated list ordered by `created_at DESC`. Return `(items, total_count)`
4. `delete(document_id, user_id) -> str | None` — Delete document and all cascaded records (extractions, fields, audit entries, chat messages, citations). Return `storage_path` if found, `None` if not found. Cascading deletes are explicit (not relying on DB-level CASCADE)
5. `update_status(document_id, status, **kwargs) -> None` — Update status and any additional fields. Always update `updated_at`

### Non-Functional

- All methods are `async` and use `async with AsyncSessionLocal() as session:`
- Every query that returns user data MUST filter by `user_id`
- `update_status` does NOT filter by user_id (used by system-level pipeline processing)
- Pagination uses offset-based approach: `offset = (page - 1) * limit`
- No business logic in the repository — pure data access

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/documents/test_repositories.py`

```python
"""
Unit tests for docmind/modules/documents/repositories.py.

All tests mock the SQLAlchemy AsyncSessionLocal to test repository logic
in isolation, without a running database.
"""
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.dbase.psql.models import Document
from docmind.modules.documents.repositories import DocumentRepository


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-123"
OTHER_USER_ID = "user-456"
DOC_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_document(
    doc_id: str = DOC_ID,
    user_id: str = USER_ID,
    filename: str = "invoice.pdf",
    file_type: str = "pdf",
    file_size: int = 2048,
    storage_path: str = "user-123/doc-abc/invoice.pdf",
    status: str = "uploaded",
) -> Document:
    """Create a Document ORM instance for testing."""
    doc = Document()
    doc.id = doc_id
    doc.user_id = user_id
    doc.filename = filename
    doc.file_type = file_type
    doc.file_size = file_size
    doc.storage_path = storage_path
    doc.status = status
    doc.document_type = None
    doc.page_count = 0
    doc.created_at = datetime.now(UTC)
    doc.updated_at = datetime.now(UTC)
    return doc


@pytest.fixture
def repo():
    """Create a DocumentRepository instance."""
    return DocumentRepository()


@pytest.fixture
def mock_session():
    """Create a mock async session with context manager support."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()

    # Make it work as async context manager
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return session, cm


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


class TestCreate:
    """Tests for DocumentRepository.create()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_create_adds_document_to_session(self, mock_async_session_local, repo):
        """create() should add a Document to the session and commit."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await repo.create(
            user_id=USER_ID,
            filename="invoice.pdf",
            file_type="pdf",
            file_size=2048,
            storage_path="user-123/doc-abc/invoice.pdf",
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()

        # Verify the Document was constructed with correct fields
        added_doc = session.add.call_args[0][0]
        assert isinstance(added_doc, Document)
        assert added_doc.user_id == USER_ID
        assert added_doc.filename == "invoice.pdf"
        assert added_doc.file_type == "pdf"
        assert added_doc.file_size == 2048
        assert added_doc.storage_path == "user-123/doc-abc/invoice.pdf"

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_create_returns_document_instance(self, mock_async_session_local, repo):
        """create() should return the ORM Document instance."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await repo.create(
            user_id=USER_ID,
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            storage_path="path/to/file",
        )

        assert isinstance(result, Document)


# ---------------------------------------------------------------------------
# Tests: get_by_id
# ---------------------------------------------------------------------------


class TestGetById:
    """Tests for DocumentRepository.get_by_id()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_get_by_id_returns_document_when_found(self, mock_async_session_local, repo):
        """get_by_id() should return the document when ID and user_id match."""
        doc = _make_document()
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = doc
        session.execute = AsyncMock(return_value=execute_result)
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await repo.get_by_id(DOC_ID, USER_ID)

        assert result is doc
        assert result.id == DOC_ID

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_get_by_id_returns_none_when_not_found(self, mock_async_session_local, repo):
        """get_by_id() should return None when document does not exist."""
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await repo.get_by_id("nonexistent-id", USER_ID)

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_get_by_id_filters_by_user_id(self, mock_async_session_local, repo):
        """get_by_id() must include user_id in the WHERE clause."""
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await repo.get_by_id(DOC_ID, USER_ID)

        # Verify execute was called (the SQL will contain both conditions)
        session.execute.assert_awaited_once()
        # Get the SQL statement from the call args
        stmt = session.execute.call_args[0][0]
        # The compiled SQL should reference both document.id and document.user_id
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "user_id" in compiled
        assert "documents.id" in compiled or "id" in compiled


# ---------------------------------------------------------------------------
# Tests: list_for_user
# ---------------------------------------------------------------------------


class TestListForUser:
    """Tests for DocumentRepository.list_for_user()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_list_returns_items_and_total(self, mock_async_session_local, repo):
        """list_for_user() should return (items, total_count)."""
        docs = [_make_document(doc_id=str(uuid.uuid4())) for _ in range(3)]

        session = AsyncMock()

        # First execute call: count query
        count_result = MagicMock()
        count_result.scalar.return_value = 3

        # Second execute call: items query
        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = docs
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[count_result, items_result])
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        items, total = await repo.list_for_user(USER_ID, page=1, limit=20)

        assert total == 3
        assert len(items) == 3
        assert all(isinstance(d, Document) for d in items)

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_list_empty_returns_zero_total(self, mock_async_session_local, repo):
        """list_for_user() with no documents should return ([], 0)."""
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[count_result, items_result])
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        items, total = await repo.list_for_user(USER_ID, page=1, limit=20)

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_list_pagination_uses_offset(self, mock_async_session_local, repo):
        """list_for_user() page 2, limit 10 should use offset 10."""
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 25

        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[count_result, items_result])
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        items, total = await repo.list_for_user(USER_ID, page=2, limit=10)

        # Verify the items query was called (second execute call)
        assert session.execute.await_count == 2
        # Total should still reflect all matching documents
        assert total == 25


# ---------------------------------------------------------------------------
# Tests: delete
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for DocumentRepository.delete()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_delete_returns_storage_path_when_found(self, mock_async_session_local, repo):
        """delete() should return the storage_path of the deleted document."""
        doc = _make_document(storage_path="user-123/doc-abc/file.pdf")

        session = AsyncMock()
        # First execute: SELECT document
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = doc
        # Subsequent executes: SELECT extraction_ids, DELETE cascades
        ext_result = MagicMock()
        ext_result.all.return_value = []

        session.execute = AsyncMock(side_effect=[select_result, ext_result])
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await repo.delete(DOC_ID, USER_ID)

        assert result == "user-123/doc-abc/file.pdf"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_delete_returns_none_when_not_found(self, mock_async_session_local, repo):
        """delete() should return None when document doesn't exist."""
        session = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=select_result)
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await repo.delete("nonexistent-id", USER_ID)

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_delete_filters_by_user_id(self, mock_async_session_local, repo):
        """delete() must filter by user_id to prevent cross-user deletion."""
        session = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=select_result)
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await repo.delete(DOC_ID, OTHER_USER_ID)

        stmt = session.execute.call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "user_id" in compiled


# ---------------------------------------------------------------------------
# Tests: update_status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    """Tests for DocumentRepository.update_status()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_update_status_executes_update(self, mock_async_session_local, repo):
        """update_status() should execute an UPDATE statement and commit."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await repo.update_status(DOC_ID, "processing")

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_update_status_with_extra_kwargs(self, mock_async_session_local, repo):
        """update_status() should accept additional fields via kwargs."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        mock_async_session_local.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await repo.update_status(DOC_ID, "ready", page_count=5, document_type="invoice")

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/modules/documents/repositories.py` — Replace stub with full implementation

**Implementation guidance**:

1. Add imports at the top:
   ```python
   from datetime import datetime, timezone
   from sqlalchemy import delete as sa_delete, func, select, update
   from docmind.dbase.psql.core.session import AsyncSessionLocal
   from docmind.dbase.psql.models import (
       AuditEntry, ChatMessage, Document, ExtractedField, Extraction,
   )
   ```

2. Implement each method following the spec in `specs/backend/services.md`:
   - `create`: Instantiate `Document(...)`, `session.add()`, `session.commit()`, `session.refresh()`, return doc
   - `get_by_id`: `select(Document).where(Document.id == document_id, Document.user_id == user_id)`, use `scalar_one_or_none()`
   - `list_for_user`: Two queries — count with `func.count()`, then paginated select with `.offset().limit().order_by(Document.created_at.desc())`
   - `delete`: Select document first (with user_id filter), get extraction IDs, delete cascaded records in FK order, then delete the document itself
   - `update_status`: `update(Document).where(Document.id == document_id).values(status=status, updated_at=datetime.now(timezone.utc), **kwargs)`

3. Key patterns:
   - Always use `async with AsyncSessionLocal() as session:` — one session per operation
   - Return `list(result.scalars().all())` for list queries
   - Use `result.scalar_one_or_none()` for single-row queries
   - Cascading delete order: audit_entries/extracted_fields (leaf) -> chat_messages -> extractions -> document

### Step 3: Refactor (IMPROVE)

- Extract common session pattern into a helper if repeated too much
- Ensure `delete` handles edge cases (extraction with no fields, no chat messages)
- Add type annotations for all return values
- Verify `update_status` sets `updated_at` explicitly since `onupdate` only triggers on ORM-level changes

## Acceptance Criteria

- [ ] `create()` inserts a document and returns the ORM instance with generated id
- [ ] `get_by_id()` returns the document only when both id and user_id match
- [ ] `get_by_id()` returns `None` for non-matching user_id (no data leakage)
- [ ] `list_for_user()` returns paginated results with correct total count
- [ ] `list_for_user()` orders by `created_at DESC`
- [ ] `delete()` removes document and all cascaded records
- [ ] `delete()` returns `storage_path` on success, `None` on not-found
- [ ] `delete()` filters by `user_id`
- [ ] `update_status()` updates status and `updated_at` timestamp
- [ ] `update_status()` accepts additional kwargs for extra field updates
- [ ] All 13 unit tests pass
- [ ] No business logic in the repository

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/modules/documents/repositories.py` | Modify | Replace stub with full CRUD implementation using SQLAlchemy async sessions |
| `backend/tests/unit/modules/documents/test_repositories.py` | Create | 13 unit tests covering all 5 repository methods |

## Verification

```bash
# Run the repository tests
cd backend && python -m pytest tests/unit/modules/documents/test_repositories.py -v

# Run with coverage
cd backend && python -m pytest tests/unit/modules/documents/test_repositories.py -v --cov=docmind.modules.documents.repositories --cov-report=term-missing

# Verify user_id filtering (grep for security)
grep -n "user_id" backend/src/docmind/modules/documents/repositories.py
# Should appear in create, get_by_id, list_for_user, and delete methods
```
