"""
Unit tests for docmind/modules/projects/usecases/.

All tests mock the repositories and services to test orchestration logic.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from docmind.dbase.psql.models import Document, Project, ProjectConversation, ProjectMessage
from docmind.modules.projects.schemas import ProjectUpdate
from docmind.modules.projects.usecases import (
    ProjectConversationUseCase,
    ProjectCRUDUseCase,
    ProjectDocumentUseCase,
)
from docmind.shared.exceptions import NotFoundException


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-123"
PROJECT_ID = str(uuid.uuid4())
DOC_ID = str(uuid.uuid4())
CONV_ID = str(uuid.uuid4())
MSG_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(
    project_id: str = PROJECT_ID,
    name: str = "Test Project",
) -> Project:
    return Project(
        id=project_id,
        user_id=USER_ID,
        name=name,
        description="Test",
        persona_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_document(doc_id: str = DOC_ID) -> Document:
    return Document(
        id=doc_id,
        user_id=USER_ID,
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="path/to/file",
        status="uploaded",
        page_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_conversation(conv_id: str = CONV_ID) -> ProjectConversation:
    conv = ProjectConversation(
        id=conv_id,
        project_id=PROJECT_ID,
        user_id=USER_ID,
        title="Chat",
        created_at=datetime.now(UTC),
    )
    return conv


def _make_message(msg_id: str = MSG_ID) -> ProjectMessage:
    return ProjectMessage(
        id=msg_id,
        conversation_id=CONV_ID,
        role="user",
        content="Hello",
        citations=None,
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_conv_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_prompt_service() -> MagicMock:
    svc = MagicMock()
    svc.validate_project_name.side_effect = lambda n: n.strip()
    svc.validate_persona_assignment.return_value = None
    return svc


@pytest.fixture
def crud_usecase(mock_repo, mock_prompt_service) -> ProjectCRUDUseCase:
    return ProjectCRUDUseCase(
        repo=mock_repo,
        prompt_service=mock_prompt_service,
    )


@pytest.fixture
def doc_usecase(mock_repo) -> ProjectDocumentUseCase:
    return ProjectDocumentUseCase(
        repo=mock_repo,
        indexing_service=MagicMock(),
        doc_repo=AsyncMock(),
        storage_service=MagicMock(),
    )


@pytest.fixture
def conv_usecase(mock_repo, mock_conv_repo) -> ProjectConversationUseCase:
    return ProjectConversationUseCase(
        repo=mock_repo,
        conv_repo=mock_conv_repo,
    )


# ---------------------------------------------------------------------------
# Tests: create_project
# ---------------------------------------------------------------------------


class TestCreateProject:

    @pytest.mark.asyncio
    async def test_creates_and_returns_response(self, crud_usecase, mock_repo):
        project = _make_project()
        mock_repo.create.return_value = project

        result = await crud_usecase.create_project(
            user_id=USER_ID,
            name="Test Project",
            description="Test",
        )

        assert result.id == PROJECT_ID
        assert result.name == "Test Project"
        assert result.document_count == 0
        mock_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validates_name(self, crud_usecase, mock_prompt_service, mock_repo):
        project = _make_project()
        mock_repo.create.return_value = project

        await crud_usecase.create_project(user_id=USER_ID, name="  Spaced  ")

        mock_prompt_service.validate_project_name.assert_called_once_with("  Spaced  ")


# ---------------------------------------------------------------------------
# Tests: get_project
# ---------------------------------------------------------------------------


class TestGetProject:

    @pytest.mark.asyncio
    async def test_returns_response_when_found(self, crud_usecase, mock_repo):
        mock_repo.get_by_id.return_value = _make_project()
        mock_repo.get_document_count.return_value = 5

        result = await crud_usecase.get_project(USER_ID, PROJECT_ID)

        assert result is not None
        assert result.id == PROJECT_ID
        assert result.document_count == 5

    @pytest.mark.asyncio
    async def test_raises_not_found_when_not_found(self, crud_usecase, mock_repo):
        mock_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await crud_usecase.get_project(USER_ID, "nonexistent")


# ---------------------------------------------------------------------------
# Tests: get_projects
# ---------------------------------------------------------------------------


class TestGetProjects:

    @pytest.mark.asyncio
    async def test_returns_paginated_list(self, crud_usecase, mock_repo):
        projects = [_make_project(project_id=str(uuid.uuid4())) for _ in range(3)]
        mock_repo.list_for_user.return_value = (projects, 3)
        mock_repo.get_document_count.return_value = 0

        result = await crud_usecase.get_projects(USER_ID, page=1, limit=20)

        assert result.total == 3
        assert len(result.items) == 3
        assert result.page == 1
        assert result.limit == 20


# ---------------------------------------------------------------------------
# Tests: update_project
# ---------------------------------------------------------------------------


class TestUpdateProject:

    @pytest.mark.asyncio
    async def test_updates_and_returns_response(self, crud_usecase, mock_repo):
        updated = _make_project(name="Updated")
        mock_repo.update.return_value = updated
        mock_repo.get_document_count.return_value = 2

        result = await crud_usecase.update_project(
            USER_ID, PROJECT_ID, ProjectUpdate(name="Updated")
        )

        assert result is not None
        assert result.name == "Updated"
        assert result.document_count == 2

    @pytest.mark.asyncio
    async def test_raises_not_found_when_not_found(self, crud_usecase, mock_repo):
        mock_repo.update.return_value = None

        with pytest.raises(NotFoundException):
            await crud_usecase.update_project(
                USER_ID, "nonexistent", ProjectUpdate(name="X")
            )


# ---------------------------------------------------------------------------
# Tests: delete_project
# ---------------------------------------------------------------------------


class TestDeleteProject:

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self, crud_usecase, mock_repo):
        mock_repo.delete.return_value = True

        result = await crud_usecase.delete_project(USER_ID, PROJECT_ID)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, crud_usecase, mock_repo):
        mock_repo.delete.return_value = False

        result = await crud_usecase.delete_project(USER_ID, "nonexistent")

        assert result is False


# ---------------------------------------------------------------------------
# Tests: add_document
# ---------------------------------------------------------------------------


class TestAddDocument:

    @pytest.mark.asyncio
    async def test_links_document(self, doc_usecase, mock_repo):
        mock_repo.get_by_id.return_value = _make_project()
        mock_repo.add_document.return_value = True

        result = await doc_usecase.add_document(USER_ID, PROJECT_ID, DOC_ID)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_project_not_found(self, doc_usecase, mock_repo):
        mock_repo.get_by_id.return_value = None

        result = await doc_usecase.add_document(USER_ID, "nonexistent", DOC_ID)

        assert result is False


# ---------------------------------------------------------------------------
# Tests: list_documents
# ---------------------------------------------------------------------------


class TestListDocuments:

    @pytest.mark.asyncio
    async def test_returns_document_list(self, doc_usecase, mock_repo):
        docs = [_make_document(doc_id=str(uuid.uuid4())) for _ in range(2)]
        mock_repo.list_documents.return_value = docs

        result = await doc_usecase.list_documents(USER_ID, PROJECT_ID)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# Tests: conversations
# ---------------------------------------------------------------------------


class TestConversations:

    @pytest.mark.asyncio
    async def test_list_conversations(self, conv_usecase, mock_repo, mock_conv_repo):
        mock_repo.get_by_id.return_value = _make_project()
        convs = [_make_conversation(conv_id=str(uuid.uuid4())) for _ in range(2)]
        mock_conv_repo.list_for_project.return_value = convs
        mock_conv_repo.get_message_count.return_value = 5

        result = await conv_usecase.list_conversations(USER_ID, PROJECT_ID)

        assert len(result) == 2
        assert result[0].message_count == 5

    @pytest.mark.asyncio
    async def test_get_conversation(self, conv_usecase, mock_conv_repo):
        conv = _make_conversation()
        conv.messages = [_make_message()]
        mock_conv_repo.get_by_id.return_value = conv

        result = await conv_usecase.get_conversation(USER_ID, CONV_ID)

        assert result is not None
        assert len(result.messages) == 1

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, conv_usecase, mock_conv_repo):
        mock_conv_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await conv_usecase.get_conversation(USER_ID, "nonexistent")

    @pytest.mark.asyncio
    async def test_delete_conversation(self, conv_usecase, mock_conv_repo):
        mock_conv_repo.delete.return_value = True

        result = await conv_usecase.delete_conversation(USER_ID, CONV_ID)

        assert result is True
