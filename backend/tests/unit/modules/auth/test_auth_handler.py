"""
Unit tests for auth handler — direct function calls with mocked usecase.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from docmind.modules.auth.apiv1.handler import (
    get_session,
    login,
    logout,
    refresh,
    signup,
)
from docmind.modules.auth.schemas import (
    AuthSessionResponse,
    AuthUserResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SessionResponse,
    SignupRequest,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_SESSION = AuthSessionResponse(
    access_token="at-123",
    refresh_token="rt-456",
    expires_in=3600,
    user=AuthUserResponse(id="uid-1", email="user@example.com"),
)

FAKE_SESSION_RESP = SessionResponse(
    user=AuthUserResponse(id="uid-1", email="user@example.com"),
)


def _mock_usecase() -> AsyncMock:
    uc = AsyncMock()
    uc.signup.return_value = FAKE_SESSION
    uc.login.return_value = FAKE_SESSION
    uc.logout.return_value = None
    uc.refresh.return_value = FAKE_SESSION
    uc.get_session.return_value = FAKE_SESSION_RESP
    return uc


def _mock_credentials(token: str = "at-123") -> MagicMock:
    creds = MagicMock()
    creds.credentials = token
    return creds


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuthHandler:
    @pytest.mark.asyncio
    async def test_signup_returns_201(self) -> None:
        uc = _mock_usecase()
        body = SignupRequest(email="user@example.com", password="secret123")
        result = await signup(body=body, usecase=uc)

        assert isinstance(result, AuthSessionResponse)
        assert result.access_token == "at-123"
        uc.signup.assert_awaited_once_with(email="user@example.com", password="secret123")

    @pytest.mark.asyncio
    async def test_login_returns_200(self) -> None:
        uc = _mock_usecase()
        body = LoginRequest(email="user@example.com", password="secret123")
        result = await login(body=body, usecase=uc)

        assert isinstance(result, AuthSessionResponse)
        assert result.user.email == "user@example.com"
        uc.login.assert_awaited_once_with(email="user@example.com", password="secret123")

    @pytest.mark.asyncio
    async def test_logout_returns_200(self) -> None:
        uc = _mock_usecase()
        creds = _mock_credentials()
        result = await logout(credentials=creds, usecase=uc)

        assert isinstance(result, MessageResponse)
        assert result.message == "Logged out successfully"
        uc.logout.assert_awaited_once_with(access_token="at-123")

    @pytest.mark.asyncio
    async def test_session_returns_200(self) -> None:
        uc = _mock_usecase()
        creds = _mock_credentials()
        result = await get_session(credentials=creds, usecase=uc)

        assert isinstance(result, SessionResponse)
        assert result.user.id == "uid-1"
        uc.get_session.assert_awaited_once_with(access_token="at-123")

    @pytest.mark.asyncio
    async def test_refresh_returns_200(self) -> None:
        uc = _mock_usecase()
        body = RefreshRequest(refresh_token="rt-456")
        result = await refresh(body=body, usecase=uc)

        assert isinstance(result, AuthSessionResponse)
        assert result.refresh_token == "rt-456"
        uc.refresh.assert_awaited_once_with(refresh_token="rt-456")
