"""
docmind/modules/auth/services/auth_service.py

Auth service that calls Supabase GoTrue REST endpoints via httpx.
"""

import httpx

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.shared.exceptions import AuthenticationException, ServiceException

logger = get_logger(__name__)


def _parse_error_message(response: httpx.Response) -> str:
    """Extract a human-readable error message from a GoTrue error response."""
    try:
        body = response.json()
        # GoTrue returns {"error": "...", "error_description": "..."} or {"msg": "..."}
        return (
            body.get("error_description")
            or body.get("msg")
            or body.get("error")
            or body.get("message")
            or f"Request failed with status {response.status_code}"
        )
    except Exception:
        return f"Request failed with status {response.status_code}"


def _build_session_dict(data: dict) -> dict:
    """Normalise a GoTrue session response into a flat dict."""
    user_data = data.get("user", {})
    return {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 0),
        "user": {
            "id": user_data.get("id", ""),
            "email": user_data.get("email", ""),
            "created_at": user_data.get("created_at"),
        },
    }


class AuthService:
    """Supabase GoTrue auth via REST."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.SUPABASE_URL
        self._api_key = settings.SUPABASE_PUBLISHABLE_KEY

    def _headers(self, *, bearer: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "apikey": self._api_key,
            "Content-Type": "application/json",
        }
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        return headers

    async def signup(self, email: str, password: str) -> dict:
        """Register a new user."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/auth/v1/signup",
                    json={"email": email, "password": password},
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("signup network error: %s", exc)
            raise ServiceException("Auth service unavailable") from exc

        if response.status_code >= 400:
            msg = _parse_error_message(response)
            if response.status_code in (400, 401, 422):
                raise AuthenticationException(msg)
            raise ServiceException(msg)

        return _build_session_dict(response.json())

    async def login(self, email: str, password: str) -> dict:
        """Authenticate with email + password."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/auth/v1/token",
                    params={"grant_type": "password"},
                    json={"email": email, "password": password},
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("login network error: %s", exc)
            raise ServiceException("Auth service unavailable") from exc

        if response.status_code >= 400:
            msg = _parse_error_message(response)
            if response.status_code in (400, 401, 422):
                raise AuthenticationException(msg)
            raise ServiceException(msg)

        return _build_session_dict(response.json())

    async def logout(self, access_token: str) -> None:
        """Invalidate the current session."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/auth/v1/logout",
                    headers=self._headers(bearer=access_token),
                )
        except httpx.HTTPError as exc:
            logger.error("logout network error: %s", exc)
            raise ServiceException("Auth service unavailable") from exc

        if response.status_code >= 400:
            msg = _parse_error_message(response)
            if response.status_code in (400, 401, 422):
                raise AuthenticationException(msg)
            raise ServiceException(msg)

    async def refresh(self, refresh_token: str) -> dict:
        """Exchange a refresh token for a new session."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/auth/v1/token",
                    params={"grant_type": "refresh_token"},
                    json={"refresh_token": refresh_token},
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("refresh network error: %s", exc)
            raise ServiceException("Auth service unavailable") from exc

        if response.status_code >= 400:
            msg = _parse_error_message(response)
            if response.status_code in (400, 401, 422):
                raise AuthenticationException(msg)
            raise ServiceException(msg)

        return _build_session_dict(response.json())

    async def get_user(self, access_token: str) -> dict:
        """Fetch the authenticated user profile."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/auth/v1/user",
                    headers=self._headers(bearer=access_token),
                )
        except httpx.HTTPError as exc:
            logger.error("get_user network error: %s", exc)
            raise ServiceException("Auth service unavailable") from exc

        if response.status_code >= 400:
            msg = _parse_error_message(response)
            if response.status_code in (400, 401, 422):
                raise AuthenticationException(msg)
            raise ServiceException(msg)

        data = response.json()
        return {
            "id": data.get("id", ""),
            "email": data.get("email", ""),
            "created_at": data.get("created_at"),
        }
