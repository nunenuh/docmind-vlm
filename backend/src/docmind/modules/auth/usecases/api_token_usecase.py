"""
API Token use case — orchestrates token service, maps to schemas.
"""

from docmind.modules.auth.schemas import (
    CreateTokenRequest,
    TokenCreatedResponse,
    TokenListResponse,
    TokenResponse,
    UpdateTokenRequest,
)
from docmind.modules.auth.services.api_token_service import ApiTokenService


class ApiTokenUseCase:
    """Orchestration for API token CRUD."""

    def __init__(self, token_service: ApiTokenService | None = None) -> None:
        self._service = token_service or ApiTokenService()

    async def create_token(
        self, user_id: str, request: CreateTokenRequest
    ) -> TokenCreatedResponse:
        result = await self._service.create_token(
            user_id=user_id,
            name=request.name,
            scopes=[s.value for s in request.scopes],
            token_type=request.token_type,
            expires_in_days=request.expires_in_days,
        )
        return TokenCreatedResponse(**result)

    async def list_tokens(self, user_id: str) -> TokenListResponse:
        tokens = await self._service.list_tokens(user_id)
        return TokenListResponse(
            tokens=[TokenResponse(**t) for t in tokens],
            total=len(tokens),
        )

    async def revoke_token(self, token_id: str, user_id: str) -> None:
        await self._service.revoke_token(token_id, user_id)

    async def update_token(
        self, token_id: str, user_id: str, request: UpdateTokenRequest
    ) -> TokenResponse:
        scopes = [s.value for s in request.scopes] if request.scopes else None
        result = await self._service.update_token(
            token_id=token_id,
            user_id=user_id,
            name=request.name,
            scopes=scopes,
        )
        return TokenResponse(**result)
