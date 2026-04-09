"""
docmind/modules/auth/usecases/auth_usecase.py

Orchestrates auth operations — maps service dicts to schema responses.
"""

from __future__ import annotations

from docmind.modules.auth.protocols import AuthServiceProtocol
from docmind.modules.auth.schemas import (
    AuthSessionResponse,
    AuthUserResponse,
    SessionResponse,
)
from docmind.modules.auth.services import AuthService


def _to_session_response(data: dict) -> AuthSessionResponse:
    user = data["user"]
    return AuthSessionResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_in=data["expires_in"],
        user=AuthUserResponse(
            id=user["id"],
            email=user["email"],
            created_at=user.get("created_at"),
        ),
    )


class AuthUseCase:
    """Auth use case — thin orchestration over AuthService."""

    def __init__(self, auth_service: AuthServiceProtocol | None = None) -> None:
        self._service: AuthServiceProtocol = auth_service or AuthService()

    async def signup(self, email: str, password: str) -> AuthSessionResponse:
        data = await self._service.signup(email, password)
        return _to_session_response(data)

    async def login(self, email: str, password: str) -> AuthSessionResponse:
        data = await self._service.login(email, password)
        return _to_session_response(data)

    async def logout(self, access_token: str) -> None:
        await self._service.logout(access_token)

    async def refresh(self, refresh_token: str) -> AuthSessionResponse:
        data = await self._service.refresh(refresh_token)
        return _to_session_response(data)

    async def get_session(self, access_token: str) -> SessionResponse:
        user_data = await self._service.get_user(access_token)
        return SessionResponse(
            user=AuthUserResponse(
                id=user_data["id"],
                email=user_data["email"],
                created_at=user_data.get("created_at"),
            ),
        )
