"""
Tests for require_scopes dependency factory.
"""

import pytest

from docmind.shared.exceptions import AuthorizationException


def _user(scopes=None, auth_method="jwt"):
    return {
        "id": "user-1",
        "email": "a@b.com",
        "scopes": scopes,
        "auth_method": auth_method,
        "token_id": "tok-1" if auth_method == "api_token" else None,
    }


@pytest.mark.asyncio
async def test_jwt_user_bypasses_scope_check():
    from docmind.core.scopes import _check_scopes

    user = _user(scopes=None, auth_method="jwt")
    result = _check_scopes(user, ["documents:read"])
    assert result == user


@pytest.mark.asyncio
async def test_api_token_with_valid_scope_passes():
    from docmind.core.scopes import _check_scopes

    user = _user(scopes=["documents:read", "documents:write"], auth_method="api_token")
    result = _check_scopes(user, ["documents:read"])
    assert result == user


@pytest.mark.asyncio
async def test_api_token_missing_scope_raises_403():
    from docmind.core.scopes import _check_scopes

    user = _user(scopes=["documents:read"], auth_method="api_token")

    with pytest.raises(AuthorizationException):
        _check_scopes(user, ["projects:write"])


@pytest.mark.asyncio
async def test_admin_scope_bypasses_all_checks():
    from docmind.core.scopes import _check_scopes

    user = _user(scopes=["admin:*"], auth_method="api_token")
    result = _check_scopes(user, ["projects:write", "documents:read"])
    assert result == user


@pytest.mark.asyncio
async def test_multiple_required_scopes_all_must_match():
    from docmind.core.scopes import _check_scopes

    user = _user(scopes=["documents:read"], auth_method="api_token")

    with pytest.raises(AuthorizationException):
        _check_scopes(user, ["documents:read", "documents:write"])
