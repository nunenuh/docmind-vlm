"""
Unit tests for ApiTokenService — mocks repository.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from docmind.dbase.psql.models.api_token import ApiToken


def _make_token_model(**overrides) -> MagicMock:
    defaults = {
        "id": "tok-1",
        "user_id": "user-1",
        "name": "My Token",
        "prefix": "dm_live_abc1",
        "hashed_secret": "",
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


def _make_service(repo_mock: AsyncMock | None = None):
    from docmind.modules.auth.services.api_token_service import ApiTokenService

    repo = repo_mock or AsyncMock()
    return ApiTokenService(repository=repo), repo


# ── create_token ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_token_returns_plain_token():
    service, repo = _make_service()
    repo.create = AsyncMock(return_value=_make_token_model())

    result = await service.create_token(
        user_id="user-1",
        name="Test Token",
        scopes=["documents:read"],
        token_type="live",
        expires_in_days=90,
    )

    assert "plain_token" in result
    assert result["plain_token"].startswith("dm_live_")
    repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_token_stores_hashed_secret():
    service, repo = _make_service()
    repo.create = AsyncMock(return_value=_make_token_model())

    await service.create_token(
        user_id="user-1",
        name="Test",
        scopes=["admin:*"],
        token_type="live",
        expires_in_days=None,
    )

    call_kwargs = repo.create.call_args.kwargs
    assert len(call_kwargs["hashed_secret"]) == 64  # SHA-256 hex
    assert call_kwargs["hashed_secret"] != call_kwargs["prefix"]


@pytest.mark.asyncio
async def test_create_test_token_has_test_prefix():
    service, repo = _make_service()
    repo.create = AsyncMock(return_value=_make_token_model(token_type="test"))

    result = await service.create_token(
        user_id="user-1",
        name="Test Token",
        scopes=["documents:read"],
        token_type="test",
        expires_in_days=30,
    )

    assert result["plain_token"].startswith("dm_test_")


# ── validate_token ────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_token_returns_user_data():
    import hashlib

    plain_token = "dm_live_abcdefghijklmnopqrstuvwxyz1234"
    hashed = hashlib.sha256(plain_token.encode()).hexdigest()
    prefix = plain_token[:12]

    service, repo = _make_service()
    repo.get_by_prefix = AsyncMock(
        return_value=_make_token_model(
            prefix=prefix,
            hashed_secret=hashed,
        )
    )
    repo.update_last_used = AsyncMock()

    result = await service.validate_token(plain_token)

    assert result["user_id"] == "user-1"
    assert result["scopes"] == ["documents:read"]
    assert result["token_id"] == "tok-1"


@pytest.mark.asyncio
async def test_validate_token_rejects_wrong_hash():
    from docmind.shared.exceptions import AuthenticationException

    service, repo = _make_service()
    repo.get_by_prefix = AsyncMock(
        return_value=_make_token_model(hashed_secret="wrong_hash")
    )

    with pytest.raises(AuthenticationException):
        await service.validate_token("dm_live_abcdefghijklmnopqrstuvwxyz1234")


@pytest.mark.asyncio
async def test_validate_token_rejects_revoked():
    from docmind.shared.exceptions import AuthenticationException

    service, repo = _make_service()
    repo.get_by_prefix = AsyncMock(
        return_value=_make_token_model(
            revoked_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
    )

    with pytest.raises(AuthenticationException):
        await service.validate_token("dm_live_abcdefghijklmnopqrstuvwxyz1234")


@pytest.mark.asyncio
async def test_validate_token_rejects_expired():
    from docmind.shared.exceptions import AuthenticationException

    service, repo = _make_service()
    repo.get_by_prefix = AsyncMock(
        return_value=_make_token_model(
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
    )

    with pytest.raises(AuthenticationException):
        await service.validate_token("dm_live_abcdefghijklmnopqrstuvwxyz1234")


@pytest.mark.asyncio
async def test_validate_token_rejects_not_found():
    from docmind.shared.exceptions import AuthenticationException

    service, repo = _make_service()
    repo.get_by_prefix = AsyncMock(return_value=None)

    with pytest.raises(AuthenticationException):
        await service.validate_token("dm_live_abcdefghijklmnopqrstuvwxyz1234")


@pytest.mark.asyncio
async def test_validate_token_rejects_invalid_prefix():
    from docmind.shared.exceptions import AuthenticationException

    service, repo = _make_service()

    with pytest.raises(AuthenticationException):
        await service.validate_token("invalid_token_format")


# ── list_tokens ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_tokens_returns_token_dicts():
    service, repo = _make_service()
    repo.list_for_user = AsyncMock(
        return_value=[_make_token_model(id="tok-1"), _make_token_model(id="tok-2")]
    )

    result = await service.list_tokens("user-1")

    assert len(result) == 2
    assert result[0]["id"] == "tok-1"
    assert "hashed_secret" not in result[0]


# ── revoke_token ──────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_token_calls_repository():
    service, repo = _make_service()
    repo.revoke = AsyncMock(return_value=True)

    result = await service.revoke_token("tok-1", "user-1")

    assert result is True
    repo.revoke.assert_awaited_once_with("tok-1", "user-1")


@pytest.mark.asyncio
async def test_revoke_token_raises_when_not_found():
    from docmind.shared.exceptions import NotFoundException

    service, repo = _make_service()
    repo.revoke = AsyncMock(return_value=False)

    with pytest.raises(NotFoundException):
        await service.revoke_token("tok-999", "user-1")
