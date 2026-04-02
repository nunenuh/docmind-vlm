"""
Unit tests for ApiTokenRepository — mocks AsyncSessionLocal.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.dbase.psql.models.api_token import ApiToken


MODULE = "docmind.modules.auth.repositories.api_token_repository"


def _make_token(**overrides) -> ApiToken:
    defaults = {
        "id": "tok-1",
        "user_id": "user-1",
        "name": "My Token",
        "prefix": "dm_live_abc1",
        "hashed_secret": "a" * 64,
        "scopes": ["documents:read"],
        "token_type": "live",
        "expires_at": None,
        "last_used_at": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "revoked_at": None,
    }
    defaults.update(overrides)
    token = MagicMock(spec=ApiToken)
    for k, v in defaults.items():
        setattr(token, k, v)
    return token


def _mock_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def mock_session():
    session = _mock_session()
    with patch(f"{MODULE}.AsyncSessionLocal", return_value=session):
        yield session


# ── create ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_inserts_and_returns_token(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    mock_session.refresh = AsyncMock()

    repo = ApiTokenRepository()
    result = await repo.create(
        user_id="user-1",
        name="Test Token",
        prefix="dm_live_abc1",
        hashed_secret="a" * 64,
        scopes=["documents:read"],
        token_type="live",
        expires_at=None,
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()
    assert result is not None


# ── get_by_prefix ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_by_prefix_returns_token(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    fake_token = _make_token()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_token
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = ApiTokenRepository()
    result = await repo.get_by_prefix("dm_live_abc1")

    assert result is not None
    assert result.prefix == "dm_live_abc1"


@pytest.mark.asyncio
async def test_get_by_prefix_returns_none_when_not_found(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = ApiTokenRepository()
    result = await repo.get_by_prefix("dm_live_xxxx")

    assert result is None


# ── list_for_user ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_for_user_returns_active_tokens(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    fake_tokens = [_make_token(id="tok-1"), _make_token(id="tok-2")]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = fake_tokens
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = ApiTokenRepository()
    result = await repo.list_for_user("user-1")

    assert len(result) == 2


# ── revoke ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_sets_revoked_at(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    fake_token = _make_token()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_token
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = ApiTokenRepository()
    result = await repo.revoke("tok-1", "user-1")

    assert result is True
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_returns_false_when_not_found(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = ApiTokenRepository()
    result = await repo.revoke("tok-999", "user-1")

    assert result is False


# ── update ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_modifies_name_and_scopes(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    fake_token = _make_token()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_token
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = ApiTokenRepository()
    result = await repo.update(
        token_id="tok-1",
        user_id="user-1",
        name="Updated Name",
        scopes=["admin:*"],
    )

    assert result is not None
    mock_session.commit.assert_awaited_once()


# ── update_last_used ──────────────────────────────────


@pytest.mark.asyncio
async def test_update_last_used_updates_timestamp(mock_session):
    from docmind.modules.auth.repositories.api_token_repository import (
        ApiTokenRepository,
    )

    mock_session.execute = AsyncMock()

    repo = ApiTokenRepository()
    await repo.update_last_used("tok-1")

    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
