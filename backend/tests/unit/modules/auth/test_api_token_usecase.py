"""
Unit tests for ApiTokenUseCase — mocks service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from docmind.modules.auth.schemas import (
    CreateTokenRequest,
    TokenCreatedResponse,
    TokenListResponse,
    TokenResponse,
    TokenScope,
    UpdateTokenRequest,
)


FAKE_TOKEN_DICT = {
    "id": "tok-1",
    "name": "My Token",
    "prefix": "dm_live_abc1",
    "scopes": ["documents:read"],
    "token_type": "live",
    "expires_at": None,
    "last_used_at": None,
    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    "revoked_at": None,
}


def _make_usecase(service_mock: AsyncMock | None = None):
    from docmind.modules.auth.usecases.api_token_usecase import ApiTokenUseCase

    svc = service_mock or AsyncMock()
    return ApiTokenUseCase(token_service=svc), svc


@pytest.mark.asyncio
async def test_create_token_returns_created_response():
    uc, svc = _make_usecase()
    svc.create_token = AsyncMock(
        return_value={**FAKE_TOKEN_DICT, "plain_token": "dm_live_abc123xyz"}
    )

    request = CreateTokenRequest(
        name="My Token",
        scopes=[TokenScope.DOCUMENTS_READ],
        token_type="live",
    )
    result = await uc.create_token("user-1", request)

    assert isinstance(result, TokenCreatedResponse)
    assert result.plain_token == "dm_live_abc123xyz"
    assert result.prefix == "dm_live_abc1"


@pytest.mark.asyncio
async def test_list_tokens_returns_list_response():
    uc, svc = _make_usecase()
    svc.list_tokens = AsyncMock(
        return_value=[FAKE_TOKEN_DICT, {**FAKE_TOKEN_DICT, "id": "tok-2"}]
    )

    result = await uc.list_tokens("user-1")

    assert isinstance(result, TokenListResponse)
    assert result.total == 2
    assert len(result.tokens) == 2


@pytest.mark.asyncio
async def test_revoke_token_calls_service():
    uc, svc = _make_usecase()
    svc.revoke_token = AsyncMock(return_value=True)

    await uc.revoke_token("tok-1", "user-1")

    svc.revoke_token.assert_awaited_once_with("tok-1", "user-1")


@pytest.mark.asyncio
async def test_update_token_returns_response():
    uc, svc = _make_usecase()
    svc.update_token = AsyncMock(
        return_value={**FAKE_TOKEN_DICT, "name": "Updated"}
    )

    request = UpdateTokenRequest(name="Updated")
    result = await uc.update_token("tok-1", "user-1", request)

    assert isinstance(result, TokenResponse)
    assert result.name == "Updated"
