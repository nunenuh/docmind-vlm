"""
Unit tests for docmind/modules/projects/repositories.py.

All tests mock the SQLAlchemy AsyncSessionLocal to test repository logic
in isolation, without a running database.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.dbase.psql.models import Document, Project, ProjectConversation, ProjectMessage
from docmind.modules.projects.repositories import (
    ConversationRepository,
    ProjectRepository,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-123"
OTHER_USER_ID = "user-456"
PROJECT_ID = str(uuid.uuid4())
DOC_ID = str(uuid.uuid4())
CONV_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(
    project_id: str = PROJECT_ID,
    user_id: str = USER_ID,
    name: str = "Test Project",
    description: str | None = "A test project",
    persona_id: str | None = None,
) -> Project:
    """Create a Project ORM instance for testing."""
    return Project(
        id=project_id,
        user_id=user_id,
        name=name,
        description=description,
        persona_id=persona_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_document(
    doc_id: str = DOC_ID,
    user_id: str = USER_ID,
    project_id: str | None = None,
) -> Document:
    """Create a Document ORM instance for testing."""
    return Document(
        id=doc_id,
        user_id=user_id,
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="path/to/file",
        status="uploaded",
        project_id=project_id,
        page_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_conversation(
    conv_id: str = CONV_ID,
    project_id: str = PROJECT_ID,
    user_id: str = USER_ID,
) -> ProjectConversation:
    """Create a ProjectConversation ORM instance for testing."""
    return ProjectConversation(
        id=conv_id,
        project_id=project_id,
        user_id=user_id,
        title="Test Conversation",
        created_at=datetime.now(UTC),
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
def repo() -> ProjectRepository:
    return ProjectRepository()


@pytest.fixture
def conv_repo() -> ConversationRepository:
    return ConversationRepository()


# ===========================================================================
# ProjectRepository Tests
# ===========================================================================


class TestProjectCreate:
    """Tests for ProjectRepository.create()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_create_adds_project_and_commits(self, mock_factory, repo):
        """create() should add a Project, commit, and refresh."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.create(
            user_id=USER_ID,
            name="My Project",
            description="A description",
            persona_id=None,
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()

        added = session.add.call_args[0][0]
        assert isinstance(added, Project)
        assert added.user_id == USER_ID
        assert added.name == "My Project"

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_create_returns_project_instance(self, mock_factory, repo):
        """create() should return the ORM Project instance."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.create(
            user_id=USER_ID,
            name="Test",
        )

        assert isinstance(result, Project)


class TestProjectGetById:
    """Tests for ProjectRepository.get_by_id()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_project_when_found(self, mock_factory, repo):
        project = _make_project()
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.get_by_id(PROJECT_ID, USER_ID)

        assert result is project

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_none_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.get_by_id("nonexistent", USER_ID)

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_filters_by_user_id(self, mock_factory, repo):
        """The SELECT WHERE clause must include user_id."""
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.get_by_id(PROJECT_ID, USER_ID)

        stmt = session.execute.call_args[0][0]
        _assert_where_contains(stmt, "user_id")


class TestProjectListForUser:
    """Tests for ProjectRepository.list_for_user()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_items_and_total(self, mock_factory, repo):
        projects = [_make_project(project_id=str(uuid.uuid4())) for _ in range(3)]
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 3

        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = projects
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[count_result, items_result])
        mock_factory.return_value = _mock_session_ctx(session)

        items, total = await repo.list_for_user(USER_ID, page=1, limit=20)

        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
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
    async def test_page_zero_raises_value_error(self, repo):
        """page < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            await repo.list_for_user(USER_ID, page=0, limit=10)


class TestProjectUpdate:
    """Tests for ProjectRepository.update()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_none_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.update(PROJECT_ID, USER_ID, name="New Name")

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_update_executes_and_commits(self, mock_factory, repo):
        project = _make_project()
        session = AsyncMock()

        # First call: SELECT to check existence, returns project
        # Second call: UPDATE
        # Third call: Re-fetch SELECT, returns updated project
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = project

        update_result = MagicMock()

        refetch_result = MagicMock()
        refetch_result.scalar_one_or_none.return_value = project

        session.execute = AsyncMock(
            side_effect=[select_result, update_result, refetch_result]
        )
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.update(PROJECT_ID, USER_ID, name="Updated")

        assert result is project
        session.commit.assert_awaited_once()


class TestProjectDelete:
    """Tests for ProjectRepository.delete()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_true_when_deleted(self, mock_factory, repo):
        project = _make_project()
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = project

        # SELECT project, SELECT conv_ids (empty), DELETE convs, UPDATE docs unlink, DELETE project
        conv_result = MagicMock()
        conv_result.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[select_result, conv_result, MagicMock(), MagicMock()]
        )
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete(PROJECT_ID, USER_ID)

        assert result is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_false_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        session.rollback = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=select_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete("nonexistent", USER_ID)

        assert result is False

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_filters_by_user_id(self, mock_factory, repo):
        """delete() must filter by user_id."""
        session = AsyncMock()
        session.rollback = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=select_result)
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.delete(PROJECT_ID, OTHER_USER_ID)

        stmt = session.execute.call_args[0][0]
        _assert_where_contains(stmt, "user_id")

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_rollback_on_failure(self, mock_factory, repo):
        """delete() should rollback if an operation fails."""
        project = _make_project()
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = project

        session.execute = AsyncMock(
            side_effect=[select_result, RuntimeError("DB timeout")]
        )
        session.rollback = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        with pytest.raises(RuntimeError, match="DB timeout"):
            await repo.delete(PROJECT_ID, USER_ID)

        session.rollback.assert_awaited_once()


class TestProjectAddDocument:
    """Tests for ProjectRepository.add_document()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_true_when_linked(self, mock_factory, repo):
        session = AsyncMock()
        update_result = MagicMock()
        update_result.rowcount = 1
        session.execute = AsyncMock(return_value=update_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.add_document(PROJECT_ID, DOC_ID)

        assert result is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_false_when_doc_not_found(self, mock_factory, repo):
        session = AsyncMock()
        update_result = MagicMock()
        update_result.rowcount = 0
        session.execute = AsyncMock(return_value=update_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.add_document(PROJECT_ID, "nonexistent")

        assert result is False


class TestProjectRemoveDocument:
    """Tests for ProjectRepository.remove_document()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_true_when_unlinked(self, mock_factory, repo):
        session = AsyncMock()
        update_result = MagicMock()
        update_result.rowcount = 1
        session.execute = AsyncMock(return_value=update_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.remove_document(PROJECT_ID, DOC_ID)

        assert result is True

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_false_when_not_linked(self, mock_factory, repo):
        session = AsyncMock()
        update_result = MagicMock()
        update_result.rowcount = 0
        session.execute = AsyncMock(return_value=update_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.remove_document(PROJECT_ID, "nonexistent")

        assert result is False


class TestProjectListDocuments:
    """Tests for ProjectRepository.list_documents()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_documents(self, mock_factory, repo):
        docs = [_make_document(doc_id=str(uuid.uuid4()), project_id=PROJECT_ID) for _ in range(2)]
        session = AsyncMock()

        # First: verify project ownership
        proj_result = MagicMock()
        proj_result.scalar_one_or_none.return_value = PROJECT_ID

        # Second: list documents
        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = docs
        items_result.scalars.return_value = scalars_mock

        session.execute = AsyncMock(side_effect=[proj_result, items_result])
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.list_documents(PROJECT_ID, USER_ID)

        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_empty_when_project_not_owned(self, mock_factory, repo):
        session = AsyncMock()
        proj_result = MagicMock()
        proj_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=proj_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.list_documents(PROJECT_ID, OTHER_USER_ID)

        assert result == []


# ===========================================================================
# ConversationRepository Tests
# ===========================================================================


class TestConversationCreate:
    """Tests for ConversationRepository.create()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_create_adds_and_commits(self, mock_factory, conv_repo):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await conv_repo.create(
            project_id=PROJECT_ID,
            user_id=USER_ID,
            title="Test Chat",
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()

        added = session.add.call_args[0][0]
        assert isinstance(added, ProjectConversation)
        assert added.project_id == PROJECT_ID
        assert added.user_id == USER_ID


class TestConversationGetById:
    """Tests for ConversationRepository.get_by_id()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_conversation_when_found(self, mock_factory, conv_repo):
        conv = _make_conversation()
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = conv
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await conv_repo.get_by_id(CONV_ID, USER_ID)

        assert result is conv

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_none_when_not_found(self, mock_factory, conv_repo):
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await conv_repo.get_by_id("nonexistent", USER_ID)

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_filters_by_user_id(self, mock_factory, conv_repo):
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        await conv_repo.get_by_id(CONV_ID, USER_ID)

        stmt = session.execute.call_args[0][0]
        _assert_where_contains(stmt, "user_id")


class TestConversationDelete:
    """Tests for ConversationRepository.delete()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_true_when_deleted(self, mock_factory, conv_repo):
        conv = _make_conversation()
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = conv

        session.execute = AsyncMock(side_effect=[select_result, MagicMock()])
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await conv_repo.delete(CONV_ID, USER_ID)

        assert result is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_returns_false_when_not_found(self, mock_factory, conv_repo):
        session = AsyncMock()
        session.rollback = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=select_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await conv_repo.delete("nonexistent", USER_ID)

        assert result is False

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_rollback_on_failure(self, mock_factory, conv_repo):
        conv = _make_conversation()
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = conv

        session.execute = AsyncMock(
            side_effect=[select_result, RuntimeError("DB error")]
        )
        session.rollback = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        with pytest.raises(RuntimeError, match="DB error"):
            await conv_repo.delete(CONV_ID, USER_ID)

        session.rollback.assert_awaited_once()


class TestConversationAddMessage:
    """Tests for ConversationRepository.add_message()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.repositories.AsyncSessionLocal")
    async def test_adds_message_and_commits(self, mock_factory, conv_repo):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await conv_repo.add_message(
            conversation_id=CONV_ID,
            role="user",
            content="Hello",
            citations=None,
        )

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert isinstance(added, ProjectMessage)
        assert added.role == "user"
        assert added.content == "Hello"
        session.commit.assert_awaited_once()
