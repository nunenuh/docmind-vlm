"""
Tests for unified get_current_user — JWT + API token dual path.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


MODULE = "docmind.core.auth"


def _make_request(auth_header: str | None = None, api_key_header: str | None = None):
    request = MagicMock()
    headers = {}
    if auth_header:
        headers["authorization"] = auth_header
    if api_key_header:
        headers["x-api-key"] = api_key_header
    request.headers = headers
    return request


@pytest.mark.asyncio
async def test_api_token_prefix_routes_to_token_validation():
    from docmind.core.auth import get_current_user

    request = _make_request(auth_header="Bearer dm_live_abcdefghijklmnop")
    mock_validate = AsyncMock(return_value={
        "user_id": "user-1",
        "scopes": ["documents:read"],
        "token_id": "tok-1",
        "auth_method": "api_token",
    })

    with patch(f"{MODULE}.ApiTokenService") as MockService:
        MockService.return_value.validate_token = mock_validate
        result = await get_current_user(request)

    assert result["id"] == "user-1"
    assert result["auth_method"] == "api_token"
    assert result["scopes"] == ["documents:read"]


@pytest.mark.asyncio
async def test_x_api_key_header_accepted():
    from docmind.core.auth import get_current_user

    request = _make_request(api_key_header="dm_live_abcdefghijklmnop")
    mock_validate = AsyncMock(return_value={
        "user_id": "user-1",
        "scopes": ["admin:*"],
        "token_id": "tok-2",
        "auth_method": "api_token",
    })

    with patch(f"{MODULE}.ApiTokenService") as MockService:
        MockService.return_value.validate_token = mock_validate
        result = await get_current_user(request)

    assert result["id"] == "user-1"
    assert result["auth_method"] == "api_token"


@pytest.mark.asyncio
async def test_jwt_token_routes_to_jwt_decode():
    from docmind.core.auth import get_current_user

    request = _make_request(auth_header="Bearer eyJhbGciOiJIUzI1NiJ9.test.sig")

    with patch(f"{MODULE}.decode_jwt", return_value={"id": "user-2", "email": "a@b.com"}):
        result = await get_current_user(request)

    assert result["id"] == "user-2"
    assert result["auth_method"] == "jwt"
    assert result["scopes"] is None


@pytest.mark.asyncio
async def test_no_token_returns_401():
    from docmind.core.auth import get_current_user

    request = _make_request()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_token_returns_401():
    from docmind.core.auth import get_current_user
    from docmind.shared.exceptions import AuthenticationException

    request = _make_request(auth_header="Bearer dm_live_invalid_token_here")

    with patch(f"{MODULE}.ApiTokenService") as MockService:
        MockService.return_value.validate_token = AsyncMock(
            side_effect=AuthenticationException("Invalid")
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)

    assert exc_info.value.status_code == 401
