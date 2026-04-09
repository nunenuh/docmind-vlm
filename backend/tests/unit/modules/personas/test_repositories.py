"""
Unit tests for docmind/modules/personas/repositories.py.

All tests mock the SQLAlchemy AsyncSessionLocal to test repository logic
in isolation, without a running database.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.dbase.psql.models import Persona
from docmind.modules.personas.repositories import PersonaRepository


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-123"
OTHER_USER_ID = "user-456"
PERSONA_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_persona(
    persona_id: str = PERSONA_ID,
    user_id: str | None = USER_ID,
    name: str = "Test Persona",
    is_preset: bool = False,
) -> Persona:
    """Create a Persona ORM instance for testing."""
    return Persona(
        id=persona_id,
        user_id=user_id,
        name=name,
        description="A test persona",
        system_prompt="You are a test assistant.",
        tone="professional",
        rules=None,
        boundaries=None,
        is_preset=is_preset,
        created_at=datetime.now(UTC),
    )


def _mock_session_ctx(session: AsyncMock) -> MagicMock:
    """Wrap a mock session to work as async context manager for AsyncSessionLocal()."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo() -> PersonaRepository:
    return PersonaRepository()


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


class TestCreate:
    """Tests for PersonaRepository.create()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_create_adds_persona_and_commits(self, mock_factory, repo):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        await repo.create(
            user_id=USER_ID,
            name="My Persona",
            system_prompt="You are helpful.",
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()

        added = session.add.call_args[0][0]
        assert isinstance(added, Persona)
        assert added.user_id == USER_ID
        assert added.name == "My Persona"
        assert added.is_preset is False

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_create_returns_persona_instance(self, mock_factory, repo):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.create(
            user_id=USER_ID,
            name="Test",
            system_prompt="prompt",
        )

        assert isinstance(result, Persona)


# ---------------------------------------------------------------------------
# Tests: list_for_user
# ---------------------------------------------------------------------------


class TestListForUser:
    """Tests for PersonaRepository.list_for_user()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_presets_and_custom(self, mock_factory, repo):
        preset = _make_persona(
            persona_id=str(uuid.uuid4()), user_id=None, is_preset=True, name="Preset"
        )
        custom = _make_persona(
            persona_id=str(uuid.uuid4()), user_id=USER_ID, name="Custom"
        )
        session = AsyncMock()
        items_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [preset, custom]
        items_result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=items_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.list_for_user(USER_ID)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# Tests: get_by_id
# ---------------------------------------------------------------------------


class TestGetById:
    """Tests for PersonaRepository.get_by_id()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_persona_when_found(self, mock_factory, repo):
        persona = _make_persona()
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = persona
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.get_by_id(PERSONA_ID)

        assert result is persona

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_none_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.get_by_id("nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# Tests: update
# ---------------------------------------------------------------------------


class TestUpdate:
    """Tests for PersonaRepository.update()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_none_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.update(PERSONA_ID, USER_ID, name="New Name")

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_none_for_preset(self, mock_factory, repo):
        """Presets cannot be updated."""
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None  # is_preset filter excludes it
        session.execute = AsyncMock(return_value=execute_result)
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.update(PERSONA_ID, USER_ID, name="Changed")

        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_update_commits_and_returns(self, mock_factory, repo):
        persona = _make_persona()
        session = AsyncMock()

        # First: SELECT finds persona
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = persona

        # Second: UPDATE
        update_result = MagicMock()

        # Third: Re-fetch
        refetch_result = MagicMock()
        refetch_result.scalar_one_or_none.return_value = persona

        session.execute = AsyncMock(
            side_effect=[select_result, update_result, refetch_result]
        )
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.update(PERSONA_ID, USER_ID, name="Updated")

        assert result is persona
        session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: delete
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for PersonaRepository.delete()."""

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_true_when_deleted(self, mock_factory, repo):
        session = AsyncMock()
        delete_result = MagicMock()
        delete_result.rowcount = 1
        session.execute = AsyncMock(return_value=delete_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete(PERSONA_ID, USER_ID)

        assert result is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_false_when_not_found(self, mock_factory, repo):
        session = AsyncMock()
        delete_result = MagicMock()
        delete_result.rowcount = 0
        session.execute = AsyncMock(return_value=delete_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete("nonexistent", USER_ID)

        assert result is False

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_can_delete_seeded_persona(self, mock_factory, repo):
        """Seeded personas (user_id=NULL) can be deleted by any user."""
        session = AsyncMock()
        delete_result = MagicMock()
        delete_result.rowcount = 1
        session.execute = AsyncMock(return_value=delete_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete(PERSONA_ID, USER_ID)

        assert result is True

    @pytest.mark.asyncio
    @patch("docmind.modules.personas.repositories.AsyncSessionLocal")
    async def test_returns_false_for_other_users_persona(self, mock_factory, repo):
        """WHERE filter excludes personas owned by other users."""
        session = AsyncMock()
        delete_result = MagicMock()
        delete_result.rowcount = 0
        session.execute = AsyncMock(return_value=delete_result)
        session.commit = AsyncMock()
        mock_factory.return_value = _mock_session_ctx(session)

        result = await repo.delete(PERSONA_ID, OTHER_USER_ID)

        assert result is False
