"""
Unit tests for docmind/modules/documents/repositories.py.

All tests mock the SQLAlchemy AsyncSessionLocal to test repository logic
in isolation, without a running database.
"""

import uuid
from datetime import UTC, datetime
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
# Helpers
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
    return Document(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=storage_path,
        status=status,
        document_type=None,
        page_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _mock_session_ctx(session: AsyncMock) -> MagicMock:
    """Wrap a mock session to work as async context manager for AsyncSessionLocal()."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _assert_where_contains(stmt: object, column_name: str) -> None:
    """Assert the compiled SQL WHERE clause contains the given column name."""
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "WHERE" in compiled, f"Statement has no WHERE clause: {compiled}"
    where_clause = compiled[compiled.index("WHERE"):]
    assert column_name in where_clause, (
        f"'{column_name}' not found in WHERE clause: {where_clause}"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo() -> DocumentRepository:
    return DocumentRepository()


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


class TestCreate:
    """Tests for DocumentRepository.create()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_create_adds_document_and_commits(self, mock_factory, repo):
        """create() should add a Document, commit, and refresh."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.create(
            user_id=USER_ID,
            filename="invoice.pdf",
            file_type="pdf",
            file_size=2048,
            storage_path="user-123/doc-abc/invoice.pdf",
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()

        added_doc = session.add.call_args[0][0]
        assert isinstance(added_doc, Document)
        assert added_doc.user_id == USER_ID
        assert added_doc.filename == "invoice.pdf"
        assert added_doc.file_type == "pdf"
        assert added_doc.file_size == 2048
        assert added_doc.storage_path == "user-123/doc-abc/invoice.pdf"

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_create_returns_document_instance(self, mock_factory, repo):
        """create() should return the ORM Document instance."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

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
    async def test_returns_document_when_found(self, mock_factory, repo):
        doc = _make_document()
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = doc
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.get_by_id(DOC_ID, USER_ID)

        assert result is doc
        assert result.id == DOC_ID

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_returns_none_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.get_by_id("nonexistent-id", USER_ID)

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_filters_by_user_id_in_where(self, mock_factory, repo):
        """The SELECT WHERE clause must include user_id."""
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.get_by_id(DOC_ID, USER_ID)

        stmt = session.execute.call_args[0][0]
        _assert_where_contains(stmt, "user_id")


# ---------------------------------------------------------------------------
# Tests: list_for_user
# ---------------------------------------------------------------------------


class TestListForUser:
    """Tests for DocumentRepository.list_for_user()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_returns_items_and_total(self, mock_factory, repo):
        docs = [_make_document(doc_id=str(uuid.uuid4())) for _ in range(3)]
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 3

        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = docs
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[count_result, items_result])
        mock_factory.return_value = _mock_session_ctx(session)

        items, total = await repo.list_for_user(USER_ID, page=1, limit=20)

        assert total == 3
        assert len(items) == 3
        assert all(isinstance(d, Document) for d in items)

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_empty_returns_zero_total(self, mock_factory, repo):
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[count_result, items_result])
        mock_factory.return_value = _mock_session_ctx(session)

        items, total = await repo.list_for_user(USER_ID, page=1, limit=20)

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_pagination_executes_two_queries(self, mock_factory, repo):
        """Page 2, limit 10 should still execute count + items queries."""
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 25

        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[count_result, items_result])
        mock_factory.return_value = _mock_session_ctx(session)

        items, total = await repo.list_for_user(USER_ID, page=2, limit=10)

        assert session.execute.await_count == 2
        assert total == 25

    @pytest.mark.asyncio
    async def test_page_zero_raises_value_error(self, repo):
        """page < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            await repo.list_for_user(USER_ID, page=0, limit=10)


# ---------------------------------------------------------------------------
# Tests: delete
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for DocumentRepository.delete()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_returns_storage_path_when_found(self, mock_factory, repo):
        doc = _make_document(storage_path="user-123/doc-abc/file.pdf")
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = doc

        ext_result = MagicMock()
        ext_result.all.return_value = []

        msg_result = MagicMock()
        msg_result.all.return_value = []

        # SELECT doc, SELECT ext_ids (empty), SELECT msg_ids (empty),
        # DELETE chat_msgs, DELETE extractions
        session.execute = AsyncMock(
            side_effect=[select_result, ext_result, msg_result, MagicMock(), MagicMock()]
        )
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete(DOC_ID, USER_ID)

        assert result == "user-123/doc-abc/file.pdf"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_returns_none_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        session.rollback = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=select_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete("nonexistent-id", USER_ID)

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_filters_by_user_id_in_where(self, mock_factory, repo):
        """delete() must filter by user_id in WHERE clause."""
        session = AsyncMock()
        session.rollback = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=select_result)
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.delete(DOC_ID, OTHER_USER_ID)

        stmt = session.execute.call_args[0][0]
        _assert_where_contains(stmt, "user_id")

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_cascading_delete_with_extractions_and_citations(self, mock_factory, repo):
        """delete() should cascade-delete all children in correct order."""
        doc = _make_document()
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = doc

        ext_result = MagicMock()
        ext_result.all.return_value = [("ext-1",), ("ext-2",)]

        msg_result = MagicMock()
        msg_result.all.return_value = [("msg-1",), ("msg-2",)]

        # SELECT doc, SELECT ext_ids, DELETE audit, DELETE fields,
        # SELECT msg_ids, DELETE citations, DELETE chat_msgs, DELETE extractions
        session.execute = AsyncMock(
            side_effect=[
                select_result, ext_result,
                MagicMock(), MagicMock(),  # audit, fields
                msg_result,
                MagicMock(),  # citations
                MagicMock(), MagicMock(),  # chat_msgs, extractions
            ]
        )
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete(DOC_ID, USER_ID)

        assert result == doc.storage_path
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()
        assert session.execute.await_count == 8

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_rollback_on_failure(self, mock_factory, repo):
        """delete() should rollback if an intermediate operation fails."""
        doc = _make_document()
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = doc

        ext_result = MagicMock()
        ext_result.all.return_value = [("ext-1",)]

        session.execute = AsyncMock(
            side_effect=[select_result, ext_result, RuntimeError("DB timeout")]
        )
        session.rollback = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        with pytest.raises(RuntimeError, match="DB timeout"):
            await repo.delete(DOC_ID, USER_ID)

        session.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: update_status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    """Tests for DocumentRepository.update_status()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_executes_update_and_commits(self, mock_factory, repo):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.update_status(DOC_ID, "processing")

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_accepts_allowed_kwargs(self, mock_factory, repo):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.update_status(DOC_ID, "ready", page_count=5, document_type="invoice")

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_disallowed_kwargs(self, repo):
        """update_status should reject fields not in the allowlist."""
        with pytest.raises(ValueError, match="unexpected fields"):
            await repo.update_status(DOC_ID, "ready", user_id="attacker")

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.repositories.AsyncSessionLocal")
    async def test_does_not_filter_by_user_id(self, mock_factory, repo):
        """update_status is system-level — WHERE clause should NOT include user_id."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.update_status(DOC_ID, "processing")

        stmt = session.execute.call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        # UPDATE SET clause won't contain user_id since we're not setting it
        assert "user_id" not in compiled
