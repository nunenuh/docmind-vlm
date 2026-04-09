"""
Unit tests for AuthUseCase — mocks the AuthService to test orchestration logic.
"""

from unittest.mock import AsyncMock

import pytest

from docmind.modules.auth.schemas import AuthSessionResponse, SessionResponse
from docmind.modules.auth.usecases import AuthUseCase
from docmind.shared.exceptions import AuthenticationException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_SESSION_DICT = {
    "access_token": "at-123",
    "refresh_token": "rt-456",
    "expires_in": 3600,
    "user": {
        "id": "uid-1",
        "email": "user@example.com",
        "created_at": "2026-01-01T00:00:00Z",
    },
}

FAKE_USER_DICT = {
    "id": "uid-1",
    "email": "user@example.com",
    "created_at": "2026-01-01T00:00:00Z",
}


def _make_mock_service() -> AsyncMock:
    svc = AsyncMock()
    svc.signup.return_value = FAKE_SESSION_DICT
    svc.login.return_value = FAKE_SESSION_DICT
    svc.logout.return_value = None
    svc.refresh.return_value = FAKE_SESSION_DICT
    svc.get_user.return_value = FAKE_USER_DICT
    return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuthUseCase:
    @pytest.mark.asyncio
    async def test_signup_returns_session_response(self) -> None:
        svc = _make_mock_service()
        uc = AuthUseCase(auth_service=svc)
        result = await uc.signup("user@example.com", "password")

        assert isinstance(result, AuthSessionResponse)
        assert result.access_token == "at-123"
        assert result.user.email == "user@example.com"
        svc.signup.assert_awaited_once_with("user@example.com", "password")

    @pytest.mark.asyncio
    async def test_login_returns_session_response(self) -> None:
        svc = _make_mock_service()
        uc = AuthUseCase(auth_service=svc)
        result = await uc.login("user@example.com", "password")

        assert isinstance(result, AuthSessionResponse)
        assert result.refresh_token == "rt-456"
        svc.login.assert_awaited_once_with("user@example.com", "password")

    @pytest.mark.asyncio
    async def test_logout_delegates_to_service(self) -> None:
        svc = _make_mock_service()
        uc = AuthUseCase(auth_service=svc)
        result = await uc.logout("at-123")

        assert result is None
        svc.logout.assert_awaited_once_with("at-123")

    @pytest.mark.asyncio
    async def test_refresh_returns_new_session(self) -> None:
        svc = _make_mock_service()
        uc = AuthUseCase(auth_service=svc)
        result = await uc.refresh("rt-456")

        assert isinstance(result, AuthSessionResponse)
        assert result.expires_in == 3600
        svc.refresh.assert_awaited_once_with("rt-456")

    @pytest.mark.asyncio
    async def test_get_session_returns_user(self) -> None:
        svc = _make_mock_service()
        uc = AuthUseCase(auth_service=svc)
        result = await uc.get_session("at-123")

        assert isinstance(result, SessionResponse)
        assert result.user.id == "uid-1"
        assert result.user.email == "user@example.com"
        svc.get_user.assert_awaited_once_with("at-123")

    @pytest.mark.asyncio
    async def test_login_propagates_auth_exception(self) -> None:
        svc = _make_mock_service()
        svc.login.side_effect = AuthenticationException("Invalid login credentials")
        uc = AuthUseCase(auth_service=svc)

        with pytest.raises(AuthenticationException, match="Invalid login credentials"):
            await uc.login("user@example.com", "wrong")
