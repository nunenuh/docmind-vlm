"""
Unit tests for AuthService — mocks httpx.AsyncClient to isolate GoTrue calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from docmind.modules.auth.services.auth_service import AuthService
from docmind.shared.exceptions import AuthenticationException, ServiceException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_SESSION = {
    "access_token": "at-123",
    "refresh_token": "rt-456",
    "expires_in": 3600,
    "user": {
        "id": "uid-1",
        "email": "user@example.com",
        "created_at": "2026-01-01T00:00:00Z",
    },
}

FAKE_USER = {
    "id": "uid-1",
    "email": "user@example.com",
    "created_at": "2026-01-01T00:00:00Z",
}


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


def _patch_settings():
    """Patch get_settings so AuthService.__init__ doesn't need real env vars."""
    mock_settings = MagicMock()
    mock_settings.SUPABASE_URL = "https://fake.supabase.co"
    mock_settings.SUPABASE_PUBLISHABLE_KEY = "fake-key"
    return patch(
        "docmind.modules.auth.services.auth_service.get_settings",
        return_value=mock_settings,
    )


def _patch_client(mock_resp: MagicMock, method: str = "post"):
    """Patch httpx.AsyncClient context manager to return mock_resp."""
    mock_client = AsyncMock()
    getattr(mock_client, method).return_value = mock_resp

    ctx = AsyncMock()
    ctx.__aenter__.return_value = mock_client
    ctx.__aexit__.return_value = None

    return patch("httpx.AsyncClient", return_value=ctx), mock_client


# ---------------------------------------------------------------------------
# signup
# ---------------------------------------------------------------------------


class TestSignup:
    @pytest.mark.asyncio
    async def test_signup_success(self) -> None:
        mock_resp = _mock_response(200, FAKE_SESSION)
        client_patch, _ = _patch_client(mock_resp)

        with _patch_settings(), client_patch:
            svc = AuthService()
            result = await svc.signup("user@example.com", "password")

        assert result["access_token"] == "at-123"
        assert result["user"]["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self) -> None:
        mock_resp = _mock_response(422, {"msg": "User already registered"})
        client_patch, _ = _patch_client(mock_resp)

        with _patch_settings(), client_patch:
            svc = AuthService()
            with pytest.raises(AuthenticationException, match="User already registered"):
                await svc.signup("dup@example.com", "password")


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        mock_resp = _mock_response(200, FAKE_SESSION)
        client_patch, _ = _patch_client(mock_resp)

        with _patch_settings(), client_patch:
            svc = AuthService()
            result = await svc.login("user@example.com", "password")

        assert result["access_token"] == "at-123"
        assert result["refresh_token"] == "rt-456"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self) -> None:
        mock_resp = _mock_response(400, {"error_description": "Invalid login credentials"})
        client_patch, _ = _patch_client(mock_resp)

        with _patch_settings(), client_patch:
            svc = AuthService()
            with pytest.raises(AuthenticationException, match="Invalid login credentials"):
                await svc.login("user@example.com", "wrong")


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_success(self) -> None:
        mock_resp = _mock_response(204)
        client_patch, _ = _patch_client(mock_resp)

        with _patch_settings(), client_patch:
            svc = AuthService()
            result = await svc.logout("at-123")

        assert result is None


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self) -> None:
        mock_resp = _mock_response(200, FAKE_SESSION)
        client_patch, _ = _patch_client(mock_resp)

        with _patch_settings(), client_patch:
            svc = AuthService()
            result = await svc.refresh("rt-456")

        assert result["access_token"] == "at-123"

    @pytest.mark.asyncio
    async def test_refresh_expired(self) -> None:
        mock_resp = _mock_response(401, {"error_description": "Token expired"})
        client_patch, _ = _patch_client(mock_resp)

        with _patch_settings(), client_patch:
            svc = AuthService()
            with pytest.raises(AuthenticationException, match="Token expired"):
                await svc.refresh("expired-rt")


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self) -> None:
        mock_resp = _mock_response(200, FAKE_USER)
        client_patch, _ = _patch_client(mock_resp, method="get")

        with _patch_settings(), client_patch:
            svc = AuthService()
            result = await svc.get_user("at-123")

        assert result["id"] == "uid-1"
        assert result["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_user_invalid_token(self) -> None:
        mock_resp = _mock_response(401, {"msg": "Invalid token"})
        client_patch, _ = _patch_client(mock_resp, method="get")

        with _patch_settings(), client_patch:
            svc = AuthService()
            with pytest.raises(AuthenticationException, match="Invalid token"):
                await svc.get_user("bad-token")
